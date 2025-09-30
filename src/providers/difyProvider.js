// UTF-8
// 说明：Dify 工作流适配器，将 difyService 的接口映射为统一 Provider 形状

import difyService from '@/services/dify'
import { v4 as uuidv4 } from 'uuid'

const difyProvider = {
  id: 'dify',
  name: 'Dify 工作流',
  // 能力矩阵：支持流式/反馈，文件上传（依赖后端配置），提供会话历史，不提供来源
  capabilities: {
    streaming: true,
    files: { enabled: true, accept: 'image/*,.pdf,.doc,.docx,.txt,.md,.json,.csv,.xlsx,.xls', maxCount: 10 },
    feedback: true,
    history: true,
    sources: false,
    editResend: true,
  },

  // 列出会话（根据上下文应用智能体配置）
  async listConversations(ctx = {}) {
    if (ctx?.agentId !== undefined) {
      difyService.applyAgent(ctx.agentId ? String(ctx.agentId) : null)
    }
    const res = await difyService.getConversations()
    const toDate = value => {
      if (!value) return new Date()
      if (typeof value === 'number') {
        return new Date(value > 1e12 ? value : value * 1000)
      }
      const d = new Date(value)
      return isNaN(d.getTime()) ? new Date() : d
    }
    const list = (res?.data || []).map(item => ({
      id: 'dify_' + item.id, // 本地映射 ID
      title: item.name || '未命名对话',
      createdAt: toDate(item.created_at),
      updatedAt: toDate(item.updated_at || item.created_at),
      provider: 'dify',
      providerConvId: item.id,
    }))
    return list
  },

  // 获取消息
  async getMessages(providerConvId, ctx = {}) {
    if (ctx?.agentId !== undefined) {
      difyService.applyAgent(ctx.agentId ? String(ctx.agentId) : null)
    }
    const res = await difyService.getConversationMessages(providerConvId)
    const data = res?.data || []
    const messages = []
    const toDate = value => {
      if (!value) return new Date()
      if (typeof value === 'number') {
        return new Date(value > 1e12 ? value : value * 1000)
      }
      const d = new Date(value)
      return isNaN(d.getTime()) ? new Date() : d
    }
    data.forEach(msg => {
      const ts = toDate(msg.created_at)
      messages.push({
        id: uuidv4(),
        role: 'user',
        content: msg.query,
        messageId: msg.id + '_user',
        provider: 'dify',
        timestamp: ts,
      })
      messages.push({
        id: uuidv4(),
        role: 'assistant',
        content: msg.answer,
        messageId: msg.id,
        provider: 'dify',
        metadata: { feedback: msg.feedback?.rating },
        timestamp: ts,
      })
    })
    return messages
  },

  // 发送消息（支持流式与文件）
  async sendMessage({ content, files = [], providerConvId, context = {}, onEvent, abortController }) {
    if (context?.agentId !== undefined) {
      difyService.applyAgent(context.agentId ? String(context.agentId) : null)
    }
    return difyService.sendMessage(
      content,
      files,
      providerConvId || null,
      (data) => {
        if (data.type === 'content') {
          onEvent?.({ type: 'content', content: data.content, messageId: data.messageId, conversationId: data.conversationId })
        } else if (data.type === 'end') {
          onEvent?.({ type: 'end', content: data.content, messageId: data.messageId, conversationId: data.conversationId, metadata: data.metadata })
        }
      },
      abortController
    )
  },

  // 删除会话
  async deleteConversation(providerConvId, ctx = {}) {
    if (ctx?.agentId !== undefined) {
      difyService.applyAgent(ctx.agentId ? String(ctx.agentId) : null)
    }
    await difyService.deleteConversation(providerConvId)
  },

  // 点赞/点踩反馈
  async feedback(messageId, rating, reason = '', ctx = {}) {
    if (ctx?.agentId !== undefined) {
      difyService.applyAgent(ctx.agentId ? String(ctx.agentId) : null)
    }
    await difyService.feedbackMessage(messageId, rating, reason)
  },
}

export default difyProvider
