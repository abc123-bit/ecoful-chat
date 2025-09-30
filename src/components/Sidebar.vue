<template>
  <div :class="['sidebar', { open: isMobileOpen, collapsed: isDesktopCollapsed }]">
    <!-- 桌面端收起状态：仅展示紧凑 Logo（收起/展开控制统一由 MainLayout 负责） -->
    <div v-if="isDesktopCollapsed" class="collapsed-sidebar">
      <div class="logo-collapsed">
        <img src="@/pagefile/logo.png" alt="Logo" class="logo-icon" />
      </div>
    </div>

    <!-- 完整侧边栏内容 -->
    <div v-else class="sidebar-content">
      <div class="sidebar-header">
        <div class="header-top">
          <div class="logo-full">
            <img src="@/pagefile/logo.png" alt="Logo" class="logo-icon" />
            <span class="app-name">粤风AI智能对话</span>
          </div>
          <!-- 收起/展开按钮移除，统一由 MainLayout 控制 -->
        </div>

        <!--
        新的对话按钮
        <button class="new-chat-btn" @click="handleNewConversation">
          <PlusOutlined />
          新的对话
        </button>
        
        -->
        <!-- 侧栏导航（统一按你的要求呈现四个板块） -->
        <router-link to="/agents" class="nav-item" active-class="is-active">
          <span class="icon">🤖</span>
          <span class="label">智能体</span>
        </router-link>
        <router-link to="/knowledge-base" class="nav-item" active-class="is-active">
          <span class="icon">🗂️</span>
          <span class="label">知识库</span>
        </router-link>
        <router-link to="/rag-chat" class="nav-item" active-class="is-active">
          <span class="icon">📚</span>
          <span class="label">知识库问答</span>
        </router-link>
        <router-link to="/history" class="nav-item" active-class="is-active">
          <span class="icon">🕘</span>
          <span class="label">历史消息</span>
        </router-link>


        <button class="refresh-history-btn" @click="$emit('refresh-history')" :disabled="isLoadingHistory">
          <ReloadOutlined v-if="!isLoadingHistory" />
          <a-spin v-else size="small" />
          刷新历史
        </button>
      </div>

      <div class="chat-history">
        <!-- 会话列表（本地与历史） -->
        <div v-for="conversation in allConversations" :key="conversation.id"
          :class="['history-item', { active: conversation.id === currentConversationId }]"
          @click="handleConversationClick(conversation)">
          <div class="conversation-info">
            <div class="history-title">{{ conversation.title }}</div>
            <div class="history-time">{{ formatTime(conversation.updatedAt || conversation.createdAt) }}</div>
          </div>

          <div class="history-actions" v-if="!conversation.originalHistoryData">
            <a-popconfirm title="确定删除这个对话吗？" @confirm="handleDeleteClick(conversation)" ok-text="删除" cancel-text="取消">
              <DeleteOutlined class="delete-btn" @click.stop />
            </a-popconfirm>
          </div>

          <!-- 历史信息的小时钟 -->
          <div class="history-indicator" v-if="conversation.originalHistoryData">
            <HistoryOutlined />
          </div>
        </div>

        <div v-if="allConversations.length === 0 && !isLoadingHistory" class="empty-history">
          <p>暂无对话记录</p>
          <a-button type="link" @click="$emit('refresh-history')">
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

    <div class="sidebar-overlay" v-if="isMobileOpen" @click="$emit('close-mobile')"></div>
  </div>
</template>

<script setup>
// 说明：本文件采用 UTF-8 编码，注释与文案使用中文
import { computed } from 'vue'
import { PlusOutlined, DeleteOutlined, HistoryOutlined, ReloadOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  conversations: { type: Array, default: () => [] },
  historyConversations: { type: Array, default: () => [] },
  currentConversationId: { type: String, default: null },
  isMobileOpen: { type: Boolean, default: false },
  isDesktopCollapsed: { type: Boolean, default: false },
  isLoadingHistory: { type: Boolean, default: false }
})

const emit = defineEmits(['new-conversation', 'select-conversation', 'delete-conversation', 'close-mobile', 'refresh-history', 'load-history-conversation'])

// 合并所有会话，按创建时间倒序；避免重复
const allConversations = computed(() => {
  const all = []
  props.conversations.forEach(conv => { all.push(conv) })
  props.historyConversations.forEach(historyConv => {
    const existsInCurrent = props.conversations.some(conv => conv.difyConversationId === historyConv.id)
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

const handleConversationClick = (conversation) => {
  if (conversation.originalHistoryData) emit('load-history-conversation', conversation.originalHistoryData)
  else emit('select-conversation', conversation.id)
}

const handleNewConversation = () => {
  // 如果存在空白“新的对话”，直接选中，否则创建
  const existingEmptyConversation = props.conversations.find(conv => conv.isEmpty && conv.title === '新的对话' && conv.messages.length === 0)
  if (existingEmptyConversation) emit('select-conversation', existingEmptyConversation.id)
  else emit('new-conversation')
}

const handleDeleteClick = (conversation) => {
  console.log('Sidebar: 删除会话请求', {
    id: conversation.id,
    title: conversation.title,
    difyConversationId: conversation.difyConversationId,
    isHistory: conversation.isHistory,
    originalHistoryData: !!conversation.originalHistoryData
  })
  emit('delete-conversation', conversation.id)
}

const formatTime = (date) => {
  if (!date) return ''
  const targetDate = date instanceof Date ? date : new Date(date)
  const now = new Date()
  const diff = now - targetDate
  const days = Math.floor(diff / 86400000)
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return targetDate.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<style scoped>
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

.sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: relative;
  transition: width .3s ease;
}

.sidebar.collapsed {
  width: 60px;
}

.collapsed-sidebar {
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.sidebar-header {
  padding: 30px 16px 16px 16px; 
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  gap: 12px;

}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}


.new-chat-btn {
  width: 100%;
  background: #fff;
  border: 1px solid #e8e8e8;
  color: #354173;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all .2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.new-chat-btn:hover {
  background: #f0f7ff;
  color: #1890ff;
  border-color: #1890ff;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #333;
  text-decoration: none;
}

.nav-item:hover {
  background: #f5f7fa;
}

.is-active {
  background: #eaf3ff;
  color: #1a73e8;
}

.icon {
  width: 20px;
  display: inline-flex;
  justify-content: center;
}

.refresh-history-btn {
  width: 100%;
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

.chat-history::-webkit-scrollbar {
  width: 4px;
}

.chat-history::-webkit-scrollbar-track {
  background: transparent;
}

.chat-history::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 2px;
}

.chat-history::-webkit-scrollbar-thumb:hover {
  background: #b8b8b8;
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

.empty-history p {
  margin-bottom: 8px;
  font-size: 13px;
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

.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, .5);
  z-index: -1;
}

/* 让侧栏内容成为满高的纵向 flex 容器，允许子项溢出滚动 */
.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  /* 关键：允许子项在 flex 中按需缩小从而触发滚动 */
}

/* 历史列表容器：占据剩余空间并启用滚动 */
.chat-history {
  flex: 1 1 auto;
  min-height: 0;
  /* 关键：避免在某些浏览器中撑开父容器 */
  overflow-y: auto;
  padding: 8px 0;
}

/* 自定义滚动条（WebKit/Chromium） */
.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-track {
  background: transparent;
}

.chat-history::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}

/* —— 响应式：中屏与小屏优化 —— */
@media (max-width: 1200px) {
  .sidebar { width: 240px; }
}

@media (max-width: 992px) {
  /* 抽屉化宽度，最大不超过 360px */
  .sidebar { width: 80vw; max-width: 360px; height: 100dvh; }
  .collapsed-sidebar { padding: 12px 6px; }
  .sidebar-header { padding-top: 20px; }
}

@media (max-width: 576px) {
  .sidebar { width: 86vw; }
  .nav-item { padding: 8px 10px; }
  .refresh-history-btn { padding: 6px 10px; }
  .history-item { padding: 10px 12px; }
}

.chat-history::-webkit-scrollbar-thumb:hover {
  background: #b8b8b8;
}

/* 自定义滚动条（Firefox） */
.chat-history {
  scrollbar-width: thin;
  scrollbar-color: #d0d0d0 transparent;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -100%;
    top: 0;
    z-index: 1000;
    transition: left .3s ease;
    width: 280px;
  }

  .sidebar.open {
    left: 0;
  }

  .sidebar.collapsed {
    width: 280px;
  }

  .collapsed-sidebar {
    display: none;
  }

  .sidebar-content {
    display: flex;
  }

  .header-top {
    display: flex;
  }

  .sidebar-overlay {
    display: block;
  }
}

@media (min-width: 769px) {
  .sidebar-overlay {
    display: none;
  }
}
</style>
