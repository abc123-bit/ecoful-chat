import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import knowledgeBaseService from '@/services/knowledgeBase'

export const useKnowledgeBaseStore = defineStore('knowledgeBase', () => {
  // 状态
  const knowledgeBases = ref([])
  const currentKnowledgeBase = ref(null)
  const files = ref([])
  const conversations = ref([])
  const currentConversation = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // 计算属性
  const hasKnowledgeBases = computed(() => knowledgeBases.value.length > 0)

  // 获取知识库列表
  const fetchKnowledgeBases = async () => {
    try {
      isLoading.value = true
      error.value = null
      const data = await knowledgeBaseService.getKnowledgeBases()
      knowledgeBases.value = data
    } catch (err) {
      error.value = err.message || '获取知识库列表失败'
      console.error('Error fetching knowledge bases:', err)
    } finally {
      isLoading.value = false
    }
  }

  // 创建知识库
  const createKnowledgeBase = async (knowledgeBaseData) => {
    try {
      isLoading.value = true
      error.value = null
      const newKb = await knowledgeBaseService.createKnowledgeBase(knowledgeBaseData)
      knowledgeBases.value.unshift(newKb)
      return newKb
    } catch (err) {
      error.value = err.message || '创建知识库失败'
      console.error('Error creating knowledge base:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // 删除知识库
  const deleteKnowledgeBase = async (id) => {
    try {
      isLoading.value = true
      error.value = null
      await knowledgeBaseService.deleteKnowledgeBase(id)
      const index = knowledgeBases.value.findIndex(kb => kb.id === id)
      if (index > -1) {
        knowledgeBases.value.splice(index, 1)
      }
      if (currentKnowledgeBase.value?.id === id) {
        currentKnowledgeBase.value = null
      }
    } catch (err) {
      error.value = err.message || '删除知识库失败'
      console.error('Error deleting knowledge base:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // 设置当前知识库
  const setCurrentKnowledgeBase = (knowledgeBase) => {
    currentKnowledgeBase.value = knowledgeBase
    files.value = []
    conversations.value = []
    currentConversation.value = null
    messages.value = []
  }

  // 获取文件列表
  const fetchFiles = async (knowledgeBaseId) => {
    try {
      isLoading.value = true
      error.value = null
      const data = await knowledgeBaseService.getFiles(knowledgeBaseId)
      files.value = data
    } catch (err) {
      error.value = err.message || '获取文件列表失败'
      console.error('Error fetching files:', err)
    } finally {
      isLoading.value = false
    }
  }

  // 上传文件
  const uploadFile = async (knowledgeBaseId, file, onProgress) => {
    try {
      error.value = null
      const uploadedFile = await knowledgeBaseService.uploadFile(knowledgeBaseId, file, onProgress)
      files.value.unshift(uploadedFile)

      // 更新知识库文件计数
      if (currentKnowledgeBase.value?.id === knowledgeBaseId) {
        currentKnowledgeBase.value.file_count += 1
      }

      return uploadedFile
    } catch (err) {
      error.value = err.message || '文件上传失败'
      console.error('Error uploading file:', err)
      throw err
    }
  }

  // 获取对话列表
  const fetchConversations = async (knowledgeBaseId) => {
    try {
      isLoading.value = true
      error.value = null
      const data = await knowledgeBaseService.getConversations(knowledgeBaseId)
      conversations.value = data
    } catch (err) {
      error.value = err.message || '获取对话列表失败'
      console.error('Error fetching conversations:', err)
    } finally {
      isLoading.value = false
    }
  }

  // 设置当前对话
  const setCurrentConversation = (conversation) => {
    currentConversation.value = conversation
    messages.value = []
  }

  // 获取对话消息
  const fetchMessages = async (conversationId) => {
    try {
      isLoading.value = true
      error.value = null
      const data = await knowledgeBaseService.getConversationMessages(conversationId)
      messages.value = data
    } catch (err) {
      error.value = err.message || '获取对话消息失败'
      console.error('Error fetching messages:', err)
    } finally {
      isLoading.value = false
    }
  }

  // 添加消息
  const addMessage = (message) => {
    messages.value.push(message)
  }

  // 更新最后一条消息
  const updateLastMessage = (content) => {
    if (messages.value.length > 0) {
      const lastMessage = messages.value[messages.value.length - 1]
      lastMessage.content = content
    }
  }

  // 清除错误
  const clearError = () => {
    error.value = null
  }

  // 重置状态
  const reset = () => {
    knowledgeBases.value = []
    currentKnowledgeBase.value = null
    files.value = []
    conversations.value = []
    currentConversation.value = null
    messages.value = []
    isLoading.value = false
    error.value = null
  }

  return {
    // 状态
    knowledgeBases,
    currentKnowledgeBase,
    files,
    conversations,
    currentConversation,
    messages,
    isLoading,
    error,

    // 计算属性
    hasKnowledgeBases,

    // 方法
    fetchKnowledgeBases,
    createKnowledgeBase,
    deleteKnowledgeBase,
    setCurrentKnowledgeBase,
    fetchFiles,
    uploadFile,
    fetchConversations,
    setCurrentConversation,
    fetchMessages,
    addMessage,
    updateLastMessage,
    clearError,
    reset
  }
})