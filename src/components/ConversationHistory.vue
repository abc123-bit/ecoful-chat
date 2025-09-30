<template>
  <div class="conversation-history">
    <div class="conversation-list">
      <a-list
        :dataSource="conversations"
        :loading="isLoading"
      >
        <template #renderItem="{ item }">
          <a-list-item
            class="conversation-item"
            @click="viewConversation(item)"
          >
            <a-list-item-meta>
              <template #title>
                <span class="conversation-title">{{ item.title || '未命名对话' }}</span>
              </template>
              <template #description>
                <div class="conversation-meta">
                  <span>{{ item.message_count || 0 }} 条消息</span>
                  <span>{{ formatTime(item.updated_at) }}</span>
                </div>
              </template>
            </a-list-item-meta>

            <template #actions>
              <a-button
                type="text"
                size="small"
                @click.stop="continueConversation(item)"
              >
                继续对话
              </a-button>
            </template>
          </a-list-item>
        </template>

        <template #header v-if="conversations.length === 0 && !isLoading">
          <a-empty description="暂无对话历史" />
        </template>
      </a-list>
    </div>

    <!-- 对话详情模态框 -->
    <a-modal
      v-model:open="showConversationModal"
      :title="selectedConversation?.title || '对话详情'"
      width="800px"
      :footer="null"
    >
      <div class="conversation-messages">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-item"
          :class="message.role"
        >
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(message.content)"></div>
            <div class="message-time">{{ formatTime(message.created_at) }}</div>
          </div>
        </div>

        <div v-if="loadingMessages" class="loading-messages">
          <a-spin size="small" />
          <span>加载消息中...</span>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { marked } from 'marked'
import dayjs from 'dayjs'

const props = defineProps({
  knowledgeBase: Object,
  conversations: Array
})

const emit = defineEmits(['refresh'])

const router = useRouter()
const kbStore = useKnowledgeBaseStore()

const showConversationModal = ref(false)
const selectedConversation = ref(null)
const loadingMessages = ref(false)

const isLoading = computed(() => kbStore.isLoading)
const messages = computed(() => kbStore.messages)

const formatTime = (time) => {
  return dayjs(time).format('MM-DD HH:mm')
}

const renderMarkdown = (content) => {
  return marked(content || '')
}

const viewConversation = async (conversation) => {
  selectedConversation.value = conversation
  showConversationModal.value = true

  try {
    loadingMessages.value = true
    await kbStore.fetchMessages(conversation.session_id)
  } catch (error) {
    console.error('Failed to load messages:', error)
  } finally {
    loadingMessages.value = false
  }
}

const continueConversation = (conversation) => {
  router.push({
    path: '/chat',
    query: {
      kb: props.knowledgeBase.id,
      conversation: conversation.session_id
    }
  })
}
</script>

<style scoped>
.conversation-history {
  padding: 16px 0;
}

.conversation-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.conversation-item:hover {
  background-color: #f5f5f5;
}

.conversation-title {
  font-weight: 500;
}

.conversation-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
}

.conversation-messages {
  max-height: 500px;
  overflow-y: auto;
  padding: 12px 0;
}

.message-item {
  margin-bottom: 16px;
  display: flex;
}

.message-item.user {
  justify-content: flex-end;
}

.message-item.user .message-content {
  background-color: #1890ff;
  color: white;
  max-width: 70%;
}

.message-item.assistant .message-content {
  background-color: #f5f5f5;
  max-width: 80%;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
}

.message-text {
  margin-bottom: 4px;
  line-height: 1.6;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
}

.loading-messages {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  font-size: 14px;
  padding: 16px;
}

:deep(.ant-list-item-meta) {
  flex: 1;
}
</style>