import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { v4 as uuidv4 } from 'uuid'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const historyConversations = ref([]) // 添加历史会话列表
  const currentConversationId = ref(null)
  const isLoading = ref(false)
  const isLoadingHistory = ref(false) // 添加历史加载状态
  const error = ref(null)
  const abortController = ref(null) // 添加中止控制器

  const currentConversation = computed(() => {
    return conversations.value.find(conv => conv.id === currentConversationId.value)
  })

  const currentMessages = computed(() => {
    return currentConversation.value?.messages || []
  })

  const createNewConversation = (title = '新的对话') => {
    const conversation = {
      id: uuidv4(),
      difyConversationId: null, // 添加Dify会话ID字段
      title,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      isEmpty: true // 标记为空会话，在发送第一条消息时会变为false
    }
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.id
    return conversation
  }

  const updateConversationDifyId = (conversationId, difyConversationId) => {
    const conversation = conversations.value.find(conv => conv.id === conversationId)
    if (conversation) {
      conversation.difyConversationId = difyConversationId
      conversation.updatedAt = new Date()
    }
  }

  const addMessage = (conversationId, message) => {
    const conversation = conversations.value.find(conv => conv.id === conversationId)
    if (conversation) {
      conversation.messages.push({
        id: uuidv4(),
        ...message,
        timestamp: new Date()
      })
      conversation.updatedAt = new Date()
      
      // 标记会话为非空（有实际消息交互）
      if (conversation.isEmpty) {
        conversation.isEmpty = false
      }
      
      // Update conversation title with first user message
      if (message.role === 'user' && conversation.messages.length === 1) {
        conversation.title = message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '')
      }
    }
  }

  const updateMessage = (conversationId, messageId, updates) => {
    const conversation = conversations.value.find(conv => conv.id === conversationId)
    if (conversation) {
      const message = conversation.messages.find(msg => msg.id === messageId)
      if (message) {
        Object.assign(message, updates)
        conversation.updatedAt = new Date()
      }
    }
  }

  const deleteConversation = (conversationId) => {
    const index = conversations.value.findIndex(conv => conv.id === conversationId)
    if (index > -1) {
      conversations.value.splice(index, 1)
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = conversations.value[0]?.id || null
      }
    }
  }

  const setCurrentConversation = (conversationId) => {
    currentConversationId.value = conversationId
  }

  const setLoading = (loading) => {
    isLoading.value = loading
  }

  const setError = (errorMessage) => {
    error.value = errorMessage
  }

  const clearError = () => {
    error.value = null
  }

  const likeMessage = (conversationId, messageId) => {
    updateMessage(conversationId, messageId, { liked: true, disliked: false })
  }

  const dislikeMessage = (conversationId, messageId) => {
    updateMessage(conversationId, messageId, { liked: false, disliked: true })
  }

  const resetMessageFeedback = (conversationId, messageId) => {
    updateMessage(conversationId, messageId, { liked: false, disliked: false })
  }

  const createAbortController = () => {
    abortController.value = new AbortController()
    return abortController.value
  }

  const abortCurrentRequest = () => {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
      setLoading(false)
    }
  }

  const clearAbortController = () => {
    abortController.value = null
  }

  const setHistoryConversations = (conversations) => {
    historyConversations.value = conversations
  }

  const setLoadingHistory = (loading) => {
    isLoadingHistory.value = loading
  }

  const loadHistoryConversation = (historyConv) => {
    // 检查是否已经存在对应的本地会话
    const existingConversation = conversations.value.find(conv => 
      conv.difyConversationId === historyConv.id
    )
    
    if (existingConversation) {
      // 如果已存在，直接切换到该会话
      currentConversationId.value = existingConversation.id
      return existingConversation
    }
    
    // 将历史会话转换为本地会话格式
    const conversation = {
      id: uuidv4(),
      difyConversationId: historyConv.id,
      title: historyConv.name || '历史对话',
      messages: [],
      createdAt: new Date(historyConv.created_at),
      updatedAt: new Date(historyConv.created_at),
      isHistory: true, // 标记为历史会话
      isEmpty: false, // 历史会话不应该被标记为空，即使暂时没有加载消息
      // 注意：不设置originalHistoryData，这样它就会显示删除按钮而不是历史图标
    }
    
    // 添加到会话列表
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.id
    
    return conversation
  }

  const loadHistoryMessages = (conversationId, messages) => {
    const conversation = conversations.value.find(conv => conv.id === conversationId)
    if (conversation) {
      // 清空现有消息
      conversation.messages = []
      
      // 添加历史消息
      messages.forEach(msg => {
        // 添加用户消息
        conversation.messages.push({
          id: uuidv4(),
          role: 'user',
          content: msg.query,
          timestamp: new Date(msg.created_at),
          messageId: msg.id + '_user'
        })
        
        // 添加助手回复
        conversation.messages.push({
          id: uuidv4(),
          role: 'assistant',
          content: msg.answer,
          timestamp: new Date(msg.created_at),
          messageId: msg.id,
          liked: msg.feedback?.rating === 'like',
          disliked: msg.feedback?.rating === 'dislike'
        })
      })
      
      conversation.updatedAt = new Date()
    }
  }

  return {
    conversations,
    historyConversations,
    currentConversationId,
    currentConversation,
    currentMessages,
    isLoading,
    isLoadingHistory,
    error,
    abortController,
    createNewConversation,
    updateConversationDifyId,
    addMessage,
    updateMessage,
    deleteConversation,
    setCurrentConversation,
    setLoading,
    setError,
    clearError,
    likeMessage,
    dislikeMessage,
    resetMessageFeedback,
    createAbortController,
    abortCurrentRequest,
    clearAbortController,
    setHistoryConversations,
    setLoadingHistory,
    loadHistoryConversation,
    loadHistoryMessages
  }
})