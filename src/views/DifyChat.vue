<template>
  <div class="chat-layout">
    <MainChat
      :conversation="currentConversation"
      :messages="currentMessages"
      :is-loading="isLoading"
      :error="error"
      :is-sidebar-collapsed="isDesktopSidebarCollapsed"
      @send-message="handleSendMessage"
      @stop-generation="handleStopGeneration"
      @toggle-sidebar="isMobileSidebarOpen = !isMobileSidebarOpen"
      @toggle-desktop-sidebar="isDesktopSidebarCollapsed = !isDesktopSidebarCollapsed"
      @like-message="handleLikeMessage"
      @dislike-message="handleDislikeMessage"
      @copy-message="handleCopyMessage"
    />
  </div>
</template>

<script setup>
// 说明：本文件采用 UTF-8 编码，注释与文案使用中文
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import difyService from '@/services/dify'
import { copyToClipboard } from '@/utils/helpers'
import MainChat from '@/components/MainChat.vue'
import { useRoute } from 'vue-router'

const chatStore = useChatStore()
const kbStore = useKnowledgeBaseStore()
const isMobileSidebarOpen = ref(false)
const isDesktopSidebarCollapsed = ref(false)

// 获取 URL 参数（知识库 ID / 会话 ID / 智能体 ID）
const route = useRoute()
const urlParams = new URLSearchParams(window.location.search)
const knowledgeBaseId = urlParams.get('kb')
const conversationId = urlParams.get('conversation')
const agentId = computed(() => route.query?.id || null)
const routeConversationId = computed(() => route.query?.conversation || null)

// 派生状态
const conversations = computed(() => chatStore.conversations)
const historyConversations = computed(() => chatStore.historyConversations)
const currentConversationId = computed(() => chatStore.currentConversationId)
const currentConversation = computed(() => chatStore.currentConversation)
const currentMessages = computed(() => chatStore.currentMessages)
const isLoading = computed(() => chatStore.isLoading)
const isLoadingHistory = computed(() => chatStore.isLoadingHistory)
const error = computed(() => chatStore.error)

// 创建新会话（避免重复空会话）
const handleNewConversation = () => {
  const existingEmptyConversation = conversations.value.find(conv =>
    conv.isEmpty && conv.title === '新的对话' && conv.messages.length === 0
  )

  if (existingEmptyConversation) {
    // 如果存在空的“新的对话”会话，直接切换到它
    chatStore.setCurrentConversation(existingEmptyConversation.id)
  } else {
    // 清理其他空会话后新建
    cleanupEmptyConversations()
    chatStore.createNewConversation()
  }
  isMobileSidebarOpen.value = false
}

// 清理空会话（仅清理标题为“新的对话”的空会话）
const cleanupEmptyConversations = () => {
  const emptyConversations = conversations.value.filter(conv =>
    conv.isEmpty &&
    conv.messages.length === 0 &&
    conv.id !== currentConversationId.value &&
    conv.title === '新的对话'
  )
  emptyConversations.forEach(conv => chatStore.deleteConversation(conv.id))
}

// 选择会话
const handleSelectConversation = (conversationId) => {
  cleanupEmptyConversations()
  chatStore.setCurrentConversation(conversationId)
  isMobileSidebarOpen.value = false
}

// 删除会话（包含历史会话联动删除）
const handleDeleteConversation = async (conversationId) => {
  try {
    console.log('删除会话请求:', conversationId)
    const conversation = conversations.value.find(conv => conv.id === conversationId)
    if (!conversation) {
      console.error('要删除的会话不存在', conversationId)
      message.error('会话不存在')
      return
    }

    console.log('找到要删除的会话:', {
      id: conversation.id,
      title: conversation.title,
      difyConversationId: conversation.difyConversationId,
      isHistory: conversation.isHistory
    })

    // 如果有 Dify 会话 ID，则先尝试从服务器删除
    if (conversation.difyConversationId) {
      console.log('准备从 Dify 服务器删除会话', conversation.difyConversationId)
      try {
        await difyService.deleteConversation(conversation.difyConversationId)
        console.log('已从 Dify 服务器删除会话', conversation.difyConversationId)
        // 同步移除历史列表中该项
        const updatedHistoryConversations = historyConversations.value.filter(
          historyConv => historyConv.id !== conversation.difyConversationId
        )
        console.log('从历史列表中移除会话，剩余会话数:', updatedHistoryConversations.length)
        chatStore.setHistoryConversations(updatedHistoryConversations)
      } catch (error) {
        console.warn('向 Dify 服务器删除会话失败', error)
        // 即使服务器删除失败，也继续删除本地会话
      }
    }

    // 删除本地会话
    chatStore.deleteConversation(conversationId)
    message.success('对话已删除')
  } catch (error) {
    console.error('删除会话失败:', error)
    message.error('删除失败: ' + (error.message || '未知错误'))
  }
}

// 发送消息（支持文件）
const handleSendMessage = async (content, files = []) => {
  if (!content.trim() && files.length === 0) return

  let conversation = currentConversation.value
  if (!conversation) {
    conversation = chatStore.createNewConversation()
  }

  // 添加用户消息（包含文件展示信息）
  chatStore.addMessage(conversation.id, {
    role: 'user',
    content: content.trim(),
    files
  })

  chatStore.setLoading(true)
  chatStore.clearError()

  // 创建中止控制器
  const abortController = chatStore.createAbortController()

  try {
    let assistantMessageId = null
    let assistantContent = ''

    await difyService.sendMessage(
      content.trim(),
      files,
      conversation.difyConversationId, // 使用 Dify 的会话 ID（可能为 null）
      (data) => {
        if (data.type === 'content') {
          assistantContent = data.content
          if (data.conversationId && !conversation.difyConversationId) {
            chatStore.updateConversationDifyId(conversation.id, data.conversationId)
          }
          if (!assistantMessageId) {
            chatStore.addMessage(conversation.id, { role: 'assistant', content: assistantContent, messageId: data.messageId })
            assistantMessageId = chatStore.currentMessages[chatStore.currentMessages.length - 1].id
          } else {
            chatStore.updateMessage(conversation.id, assistantMessageId, { content: assistantContent })
          }
        } else if (data.type === 'end') {
          if (data.conversationId && !conversation.difyConversationId) {
            chatStore.updateConversationDifyId(conversation.id, data.conversationId)
          }
          if (assistantMessageId) {
            chatStore.updateMessage(conversation.id, assistantMessageId, {
              content: data.content,
              messageId: data.messageId,
              metadata: data.metadata
            })
          }
        }
      },
      abortController
    )
  } catch (error) {
    console.error('发送消息出错:', error)
    if (error.message === '生成已停止') {
      message.info('已停止生成')
    } else if ((error.message || '').includes('文件上传')) {
      chatStore.setError(error.message)
      message.error('文件上传失败: ' + error.message)
    } else {
      chatStore.setError(error.message || '发送消息失败')
      message.error('发送消息失败，请重试')
    }
  } finally {
    chatStore.setLoading(false)
    chatStore.clearAbortController()
  }
}

// 停止生成
const handleStopGeneration = () => {
  chatStore.abortCurrentRequest()
  message.info('正在停止生成...')
}

// 点赞消息
const handleLikeMessage = async (messageId) => {
  try {
    const messageItem = currentMessages.value.find(msg => msg.id === messageId)
    if (messageItem?.messageId) {
      await difyService.feedbackMessage(messageItem.messageId, 'like')
    }
    chatStore.likeMessage(currentConversationId.value, messageId)
  } catch (error) {
    console.error('点赞消息失败:', error)
  }
}

// 点踩消息
const handleDislikeMessage = async (messageId) => {
  try {
    const messageItem = currentMessages.value.find(msg => msg.id === messageId)
    if (messageItem?.messageId) {
      await difyService.feedbackMessage(messageItem.messageId, 'dislike')
    }
    chatStore.dislikeMessage(currentConversationId.value, messageId)
  } catch (error) {
    console.error('点踩消息失败:', error)
  }
}

// 复制消息
const handleCopyMessage = async (content) => {
  const success = await copyToClipboard(content)
  if (success) message.success('已复制到剪贴板')
  else message.error('复制失败')
}

// 刷新历史会话
const handleRefreshHistory = async () => {
  chatStore.setLoadingHistory(true)
  try {
    const response = await difyService.getConversations()
    chatStore.setHistoryConversations(response.data || [])
    message.success('历史会话已刷新')
  } catch (error) {
    console.error('加载历史会话失败:', error)
    message.error('加载历史会话失败')
  } finally {
    chatStore.setLoadingHistory(false)
  }
}

// 加载历史会话
const handleLoadHistoryConversation = async (historyConv) => {
  try {
    // 加载前清理空会话
    cleanupEmptyConversations()
    // 转为本地会话并加载历史消息
    const conversation = chatStore.loadHistoryConversation(historyConv)
    chatStore.setLoadingHistory(true)
    const messagesResponse = await difyService.getConversationMessages(historyConv.id)
    chatStore.loadHistoryMessages(conversation.id, messagesResponse.data || [])
    isMobileSidebarOpen.value = false
    message.success('历史会话已加载')
  } catch (error) {
    console.error('加载历史会话失败:', error)
    message.error('加载历史会话失败')
  } finally {
    chatStore.setLoadingHistory(false)
  }
}

// 初始化（根据智能体 ID 应用 Dify 配置）
onMounted(async () => {
  if (agentId.value) {
    try { difyService.applyAgent(String(agentId.value)) } catch (e) { console.warn('应用智能体配置失败', e) }
  }
  cleanupEmptyConversations()
  handleRefreshHistory()
  if (conversations.value.length === 0) handleNewConversation()
  // 如果带有 conversation 查询参数，则直接打开对应历史会话
  if (routeConversationId.value) {
    await openDifyConversationById(String(routeConversationId.value))
  }
})

// 监听路由参数变化，动态切换智能体配置
watch(agentId, (id) => {
  try { difyService.applyAgent(id ? String(id) : null) } catch (e) { console.warn('切换智能体失败', e) }
})

// 根据 Dify 会话 ID 直接打开历史会话
async function openDifyConversationById(difyId) {
  try {
    cleanupEmptyConversations()
    chatStore.setLoadingHistory(true)
    const listResp = await difyService.getConversations()
    const item = (listResp?.data || []).find(x => x.id === difyId) || { id: difyId, name: '历史对话', created_at: new Date().toISOString() }
    const conversation = chatStore.loadHistoryConversation(item)
    const messagesResponse = await difyService.getConversationMessages(difyId)
    chatStore.loadHistoryMessages(conversation.id, messagesResponse.data || [])
    message.success('已打开历史会话')
  } catch (error) {
    console.error('打开历史会话失败:', error)
    message.error('打开历史会话失败')
  } finally {
    chatStore.setLoadingHistory(false)
  }
}
</script>
