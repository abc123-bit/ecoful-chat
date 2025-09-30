<template>
  <div class="app-layout">
    <aside class="sidebar-container">
      <nav :class="['app-sidebar', { open: isMobileSidebarOpen, collapsed: isDesktopSidebarCollapsed }]">
        <!-- 折叠态（桌面）：仅展示紧凑 Logo 与展开按钮 -->
        <div v-if="isDesktopSidebarCollapsed" class="collapsed-area">
          <img src="@/pagefile/logo.png" alt="Logo" class="logo-icon" />
          <button class="collapse-toggle" @click="toggleDesktop" title="展开">
            <MenuOutlined />
          </button>
        </div>

        <!-- 完整侧栏内容 -->
        <div v-else class="sidebar-content">
          <div class="sidebar-header">
            <div class="logo-full">
              <img src="@/pagefile/logo.png" alt="Logo" class="logo-icon" />
              <span class="app-name">粤风AI系统</span>
            </div>
            <button class="collapse-toggle" @click="toggleDesktop" title="收起">
              <MenuFoldOutlined />
            </button>
          </div>

          <!-- 导航入口 -->
          <router-link to="/agents" class="nav-item" active-class="is-active" @click="onNavClick">
            <span class="icon">🤖</span>
            <span class="label">智能体</span>
          </router-link>
          <router-link to="/knowledge-base" class="nav-item" active-class="is-active" @click="onNavClick">
            <span class="icon">🗂️</span>
            <span class="label">知识库</span>
          </router-link>
          <router-link :to="{ name: 'ChatHub', params: { provider: 'rag' } }" class="nav-item" active-class="is-active" @click="onNavClick">
            <span class="icon">📚</span>
            <span class="label">知识库问答</span>
          </router-link>
          <router-link to="/history" class="nav-item" active-class="is-active" @click="onNavClick">
            <span class="icon">🕘</span>
            <span class="label">历史消息</span>
          </router-link>

          <button class="refresh-history-btn" @click="handleRefreshHistory" :disabled="isLoadingHistory">
            <ReloadOutlined v-if="!isLoadingHistory" />
            <a-spin v-else size="small" />
            刷新历史
          </button>

          <!-- 会话列表（本地与历史） -->
          <div class="chat-history">
            <div v-for="conversation in allConversations" :key="conversation.id"
              :class="['history-item', { active: conversation.id === currentConversationId }]"
              @click="handleConversationClick(conversation)">
              <div class="conversation-info">
                <div class="history-title">{{ conversation.title }}</div>
                <div class="history-time">{{ formatTime(conversation.updatedAt || conversation.createdAt) }}</div>
              </div>
              <div class="history-actions" v-if="!conversation.originalHistoryData">
                <a-popconfirm title="确定删除这个对话吗？" @confirm="handleDeleteClick(conversation)" ok-text="删除"
                  cancel-text="取消">
                  <DeleteOutlined class="delete-btn" @click.stop />
                </a-popconfirm>
              </div>
              <div class="history-indicator" v-if="conversation.originalHistoryData">
                <HistoryOutlined />
              </div>
            </div>

            <div v-if="allConversations.length === 0 && !isLoadingHistory" class="empty-history">
              <p>暂无对话记录</p>
              <a-button type="link" @click="handleRefreshHistory">
                <ReloadOutlined />
                加载历史
              </a-button>
            </div>

            <div v-if="isLoadingHistory" class="loading-history">
              <a-spin size="small" />
              <span>加载历史会话...</span>
            </div>
          </div>

        </div>
      </nav>
      <!-- 移动端遮罩：放在 nav 之外，避免遮挡侧栏内部点击 -->
      <div class="sidebar-overlay" v-if="isMobileSidebarOpen" @click="isMobileSidebarOpen = false"></div>
    </aside>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <component :is="Component" :isSidebarCollapsed="isDesktopSidebarCollapsed" />
      </router-view>
      <!-- 移动端菜单按钮（小屏显示） -->
      <button class="mobile-open-btn" @click="isMobileSidebarOpen = true" title="打开菜单" aria-label="打开菜单">
        <MenuOutlined />
      </button>
    </main>
  </div>
</template>



<script setup>
// 说明：本文件采用 UTF-8 编码，注释与文案使用中文
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import difyService from '@/services/dify'
import { copyToClipboard } from '@/utils/helpers'
import MainChat from '@/components/MainChat.vue'
import { PlusOutlined, DeleteOutlined, HistoryOutlined, ReloadOutlined, MenuOutlined, MenuFoldOutlined } from '@ant-design/icons-vue'


const chatStore = useChatStore()
const kbStore = useKnowledgeBaseStore()
const isMobileSidebarOpen = ref(false)
const isDesktopSidebarCollapsed = ref(false)
const isMobile = ref(false)
const route = useRoute()

// 获取 URL 参数（知识库 ID / 会话 ID）
const urlParams = new URLSearchParams(window.location.search)
const knowledgeBaseId = urlParams.get('kb')
const conversationId = urlParams.get('conversation')

// 派生状态
const conversations = computed(() => chatStore.conversations)
const historyConversations = computed(() => chatStore.historyConversations)
const currentConversationId = computed(() => chatStore.currentConversationId)
const currentConversation = computed(() => chatStore.currentConversation)
const currentMessages = computed(() => chatStore.currentMessages)
const isLoading = computed(() => chatStore.isLoading)
const isLoadingHistory = computed(() => chatStore.isLoadingHistory)
const error = computed(() => chatStore.error)

// 合并当前会话与历史会话（避免重复）
const allConversations = computed(() => {
  const all = []
  conversations.value.forEach(conv => { all.push(conv) })
  historyConversations.value.forEach(historyConv => {
    const existsInCurrent = conversations.value.some(conv => conv.difyConversationId === historyConv.id)
    if (!existsInCurrent) {
      all.push({
        id: `history_${historyConv.id}`,
        difyConversationId: historyConv.id,
        title: historyConv.name || '未命名对话',
        createdAt: new Date(historyConv.created_at),
        updatedAt: new Date(historyConv.created_at),
        isHistory: true,
        originalHistoryData: historyConv
      })
    }
  })
  return all.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
})

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

// 侧栏项点击/删除/时间格式化（复用 Sidebar 行为）
const handleConversationClick = (conversation) => {
  if (conversation.originalHistoryData) handleLoadHistoryConversation(conversation.originalHistoryData)
  else handleSelectConversation(conversation.id)
}
const handleDeleteClick = (conversation) => { handleDeleteConversation(conversation.id) }
const formatTime = (date) => {
  if (!date) return ''
  const d = date instanceof Date ? date : new Date(date)
  const now = new Date()
  const diff = now - d
  const days = Math.floor(diff / 86400000)
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

// 统一控制：桌面折叠切换
const toggleDesktop = () => { isDesktopSidebarCollapsed.value = !isDesktopSidebarCollapsed.value }

// 自适应：监听窗口宽度，小屏默认收起侧栏
const updateMobile = () => {
  isMobile.value = window.innerWidth <= 992
  if (isMobile.value) isMobileSidebarOpen.value = false
}
onMounted(() => { updateMobile(); window.addEventListener('resize', updateMobile) })
onBeforeUnmount(() => { window.removeEventListener('resize', updateMobile) })

// 导航点击：在移动端自动关闭抽屉
const onNavClick = () => { if (isMobile.value) isMobileSidebarOpen.value = false }

// 路由变化：在移动端自动关闭抽屉，避免残留遮罩
watch(() => route.fullPath, () => { if (isMobile.value) isMobileSidebarOpen.value = false })

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

// 初始化
onMounted(async () => {
  cleanupEmptyConversations()
  handleRefreshHistory()
  if (conversations.value.length === 0) handleNewConversation()
})
</script>


<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 仅作为承载容器，不要写固定宽度 */
.sidebar-container {
  display: flex;
}

/* 右侧自适应 + 防溢出 */
.main-content {
  flex: 1;
  min-width: 0;
  /* 关键 */
  overflow: auto;
  background: #ffffff;
  height: 100vh;
}

/* 侧栏样式（并入布局，避免与其它页面冲突） */
.app-sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: relative;
  transition: width .3s ease;
}

.app-sidebar.collapsed {
  width: 60px;
}

.app-sidebar {
  will-change: width;
}

/* 中屏逐步收窄（不消失） */
@media (max-width: 1400px) {
  .app-sidebar:not(.collapsed) {
    width: 240px;
  }
}

@media (max-width: 1200px) {
  .app-sidebar:not(.collapsed) {
    width: 200px;
  }
}

.collapsed-area {
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.collapse-toggle {
  background: #fff;
  border: 1px solid #e8e8e8;
  color: #666;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: all .2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-toggle:hover {
  background: #f5f5f5;
  color: #1890ff;
}

.sidebar-header {
  padding: 30px 16px 16px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-icon {
  width: 50px;
  height: 50px;
  border-radius: 5px;
}

.app-name {
  font-size: 16px;
  font-weight: bold;
  margin-left: 8px;
  color: #354173;
}

.logo-full {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #333;
  text-decoration: none;
  margin: 10px 8px;
}

.nav-item:hover {
  background: #f5f7fa;
}

.is-active {
  background: #eaf3ff;
  color: #1a73e8;
  font-weight: bold;
}

.icon {
  width: 20px;
  display: inline-flex;
  justify-content: center;
}

.refresh-history-btn {
  width: 80%;
  background: #fff;
  border: 1px solid #e8e8e8;
  color: #354173;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all .2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  margin: 8px 12px;
}

.refresh-history-btn:hover:not(:disabled) {
  background: #f0f7ff;
  color: #1890ff;
  border-color: #1890ff;
}

.refresh-history-btn:disabled {
  opacity: .6;
  cursor: not-allowed;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.history-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin: 2px 8px;
  border-radius: 8px;
  color: #1f2328;
  cursor: pointer;
  transition: all .2s;
}

.history-item:hover {
  background: #f7f9fc;
}

.history-item.active {
  background: #f0f7ff;
  font-weight: 600;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.history-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  margin-bottom: 2px;
  color: #1f2328;
}

.history-time {
  font-size: 11px;
  color: #8e8ea0;
}

.history-actions {
  opacity: 0;
  transition: opacity .2s;
  margin-left: 8px;
}

.history-item:hover .history-actions {
  opacity: 1;
}

.history-indicator {
  margin-left: 8px;
  color: #8e8ea0;
  font-size: 12px;
}

.delete-btn {
  color: #8e8ea0;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all .2s;
}

.delete-btn:hover {
  color: #ff4d4f;
  background: rgba(255, 77, 79, .1);
}

.empty-history {
  text-align: center;
  padding: 20px;
  color: #8e8ea0;
}

.loading-history {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  color: #8e8ea0;
  font-size: 13px;
  justify-content: center;
}

/* 移动端抽屉化 */
@media (max-width: 992px) {
  .app-sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    width: 84vw;
    max-width: 360px;
    transform: translateX(-100%);
    height: 100dvh;
    box-shadow: 0 8px 24px rgba(0, 0, 0, .18);
    z-index: 1001;
  }

  .app-sidebar.open {
    transform: translateX(0);
  }

  .sidebar-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, .45);
    z-index: 1000;
  }

  .main-content {
    height: 100dvh;
  }
}

.main-content {
  transition: padding .2s ease;
}

/* 移动端菜单按钮 */
.mobile-open-btn {
  display: none;
  position: fixed;
  left: 18px;
  top: 2px;
  z-index: 900;
  width: 35px;
  height: 35px;
  border-radius: 12px;
  border: 1px solid #e6e7eb;
  background: #fff;
  color: #4B77F7;
  box-shadow: 0 4px 12px rgba(0, 0, 0, .12);
  align-items: center;
  justify-content: center;
}


.mobile-open-btn:hover {
  border-color: #c7d2fe;
}

@media (max-width: 992px) {
  .mobile-open-btn {
    display: inline-flex;
  }
}
</style>
