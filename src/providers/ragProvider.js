// UTF-8
// 说明：内部 RAG 系统适配器，将 KnowledgeBaseService 的接口映射为统一 Provider 形状

import KnowledgeBaseService from '@/services/knowledgeBase'
import { v4 as uuidv4 } from 'uuid'

const ragProvider = {
  id: 'rag',
  name: '知识库对话（RAG）',
  // 能力矩阵：支持流式、来源；不提供文件上传（当前 ask 接口未接收文件）；反馈能力暂不提供
  capabilities: {
    streaming: true,
    files: { enabled: false },
    feedback: false,
    history: true,
    sources: true,
    editResend: true,
  },

  /**
   * 列出会话
   * @param {Object} context { kbId:number }
   */
  async listConversations(context = {}) {
    const { kbId } = context
    if (!kbId) return []
    const list = await KnowledgeBaseService.getConversations(kbId)
    const toDate = value => {
      if (!value) return new Date()
      const d = new Date(value)
      return isNaN(d.getTime()) ? new Date() : d
    }
    return (list || []).map(item => ({
      id: 'rag_' + (item.session_id || item.id),
      title: item.title || `会话 ${(item.session_id || item.id || '').slice?.(0, 8)}`,
      createdAt: toDate(item.created_at || item.updated_at),
      updatedAt: toDate(item.updated_at || item.created_at),
      provider: 'rag',
      providerConvId: item.session_id || item.id,
    }))
  },

  // 获取消息
  async getMessages(providerConvId) {
    const list = await KnowledgeBaseService.getConversationMessages(providerConvId)
    const toDate = value => {
      if (!value) return new Date()
      const d = new Date(value)
      return isNaN(d.getTime()) ? new Date() : d
    }
    return (list || []).map(m => ({
      id: uuidv4(),
      role: m.role,
      content: m.content,
      sources: Array.isArray(m.source_files) ? m.source_files : [],
      provider: 'rag',
      timestamp: toDate(m.created_at || m.updated_at),
    }))
  },

  /**
   * 发送消息（流式）
   * @param {Object} payload { content, providerConvId, context:{kbId,maxChunks?}, onEvent, abortController }
   */
  async sendMessage({ content, providerConvId, context = {}, onEvent, abortController }) {
    const { kbId, maxChunks = 6 } = context
    if (!kbId) throw new Error('请先选择一个知识库')
    const req = {
      knowledge_base_id: kbId,
      question: content,
      conversation_id: providerConvId || null,
      max_chunks: maxChunks
    }
    return KnowledgeBaseService.askQuestionStream(
      req,
      (evt) => {
        if (!evt) return
        if (evt.type === 'start') {
          onEvent?.({ type: 'start', conversationId: evt.conversation_id || null })
        } else if (evt.type === 'content') {
          onEvent?.({ type: 'content', content: String(evt.content || '') })
        } else if (evt.type === 'end') {
          onEvent?.({ type: 'end', content: String(evt.answer || ''), sources: evt.sources || evt.sources_file_detail || [] })
        }
      },
      abortController
    )
  },

  // 删除会话（若后端提供，后续接入；当前不做）
  async deleteConversation() {
    // 占位：后端提供相应 API 后在此实现
    return
  },

  // 反馈（当前后端未提供，禁用）
  async feedback() {
    return
  },
}

export default ragProvider
