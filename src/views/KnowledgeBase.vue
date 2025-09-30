<template>
  <div class="knowledge-base-layout">
    <!-- 侧边栏 -->
    <div class="kb-sidebar">
      <div class="kb-sidebar-header">
        <h1 >知识库</h1>
        <a-button type="primary" @click="showCreateModal = true" :icon="h(PlusOutlined)">
          新建知识库
        </a-button>
      </div>

      <div class="kb-list">
        <a-spin :spinning="isLoading">
          <div v-if="!hasKnowledgeBases && !isLoading" class="empty-state">
            <a-empty description="暂无知识库">
              <a-button type="primary" @click="showCreateModal = true">
                创建第一个知识库
              </a-button>
            </a-empty>
          </div>

          <div
            v-for="kb in knowledgeBases"
            :key="kb.id"
            class="kb-item"
            :class="{ active: currentKnowledgeBase?.id === kb.id }"
            @click="selectKnowledgeBase(kb)"
          >
            <div class="kb-item-content">
              <h3>{{ kb.name }}</h3>
              <p class="description">{{ kb.description || '暂无描述' }}</p>
              <div class="kb-stats">
                <span>{{ kb.file_count }} 个文件</span>
                <span>{{ kb.document_count }} 个文档块</span>
              </div>
            </div>
            <a-dropdown :trigger="['click']">
              <a-button type="text" size="small" @click.stop>
                <template #icon>
                  <MoreOutlined />
                </template>
              </a-button>
              <template #overlay>
                <a-menu>
                  <a-menu-item @click="editKnowledgeBase(kb)">编辑</a-menu-item>
                  <a-menu-item @click="deleteKb(kb)" danger>删除</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </a-spin>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="kb-main">
      <div v-if="!currentKnowledgeBase" class="welcome-content">
        <a-empty description="请选择一个知识库开始管理">
          <a-button type="primary" @click="showCreateModal = true">创建知识库</a-button>
        </a-empty>
      </div>

      <div v-else class="kb-content">
        <!-- 头部信息 -->
        <div class="kb-header">
          <div class="kb-info">
            <h1>{{ currentKnowledgeBase.name }}</h1>
            <p>{{ currentKnowledgeBase.description || '暂无描述' }}</p>
          </div>
          <div class="kb-actions">
            <a-button danger type="primary" @click="$router.push(`rag-chat/:kbId=${currentKnowledgeBase.id}`)">开始AI问答</a-button>
            <a-upload
              :before-upload="beforeUpload"
              :custom-request="handleUpload"
              multiple
              :show-upload-list="false"
            >
              <a-button type="primary" :icon="h(UploadOutlined)">上传文件</a-button>
            </a-upload>
          </div>
        </div>

        <!-- 标签页 -->
        <a-tabs v-model:activeKey="activeTab" class="kb-tabs">
          <a-tab-pane key="files" tab="文件管理">
            <FileManager
              :knowledge-base="currentKnowledgeBase"
              :files="files"
              @refresh="refreshFiles"
            />
          </a-tab-pane>
          <a-tab-pane key="conversations" tab="对话历史">
            <ConversationHistory
              :knowledge-base="currentKnowledgeBase"
              :conversations="conversations"
              @refresh="refreshConversations"
            />
          </a-tab-pane>
          <a-tab-pane key="settings" tab="设置">
            <KnowledgeBaseSettings
              :knowledge-base="currentKnowledgeBase"
              @updated="handleKbUpdated"
            />
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>

    <!-- 创建知识库模态框 -->
    <a-modal
      v-model:open="showCreateModal"
      title="创建知识库"
      @ok="handleCreateKb"
      @cancel="resetCreateForm"
      :confirm-loading="isLoading"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="知识库名称" required>
          <a-input
            v-model:value="createForm.name"
            placeholder="请输入知识库名称"
            :maxlength="255"
            show-count
          />
        </a-form-item>

        <a-form-item label="描述">
          <a-textarea
            v-model:value="createForm.description"
            placeholder="请输入知识库描述1"
            :rows="3"
            :maxlength="100"
            show-count
          />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="分块大小">
              <a-input-number
                v-model:value="createForm.chunk_size"
                :min="100"
                :max="4000"
                placeholder="1000"
                style="width: 100%"
              />
              <div class="form-help">建议 1000-2000 字符</div>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="重叠大小">
              <a-input-number
                v-model:value="createForm.chunk_overlap"
                :min="0"
                :max="1000"
                placeholder="200"
                style="width: 100%"
              />
              <div class="form-help">建议 100-300 字符</div>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
  
</template>

<script setup>
// 说明：本文件采用 UTF-8 编码，注释与文案使用中文
import { ref, computed, onMounted, h } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, MoreOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import FileManager from '@/components/FileManager.vue'
import ConversationHistory from '@/components/ConversationHistory.vue'
import KnowledgeBaseSettings from '@/components/KnowledgeBaseSettings.vue'

const kbStore = useKnowledgeBaseStore()

// 界面状态
const showCreateModal = ref(false)
const activeTab = ref('files')

// 新建知识库表单
const createForm = ref({
  name: '',
  description: '',
  chunk_size: 1000,
  chunk_overlap: 200
})

// 计算属性
const knowledgeBases = computed(() => kbStore.knowledgeBases)
const currentKnowledgeBase = computed(() => kbStore.currentKnowledgeBase)
const files = computed(() => kbStore.files)
const conversations = computed(() => kbStore.conversations)
const hasKnowledgeBases = computed(() => kbStore.hasKnowledgeBases)
const isLoading = computed(() => kbStore.isLoading)
const error = computed(() => kbStore.error)

// 选择知识库并加载相关数据
const selectKnowledgeBase = async (kb) => {
  kbStore.setCurrentKnowledgeBase(kb)
  await Promise.all([
    refreshFiles(),
    refreshConversations()
  ])
}

// 刷新文件列表
const refreshFiles = async () => {
  if (currentKnowledgeBase.value) {
    await kbStore.fetchFiles(currentKnowledgeBase.value.id)
  }
}

// 刷新对话列表
const refreshConversations = async () => {
  if (currentKnowledgeBase.value) {
    await kbStore.fetchConversations(currentKnowledgeBase.value.id)
  }
}

// 创建知识库
const handleCreateKb = async () => {
  if (!createForm.value.name.trim()) {
    message.error('请输入知识库名称')
    return
  }
  try {
    const newKb = await kbStore.createKnowledgeBase(createForm.value)
    message.success('知识库创建成功')
    showCreateModal.value = false
    resetCreateForm()
    selectKnowledgeBase(newKb)
  } catch (err) {
    message.error(err.message || '创建失败')
  }
}

// 重置表单
const resetCreateForm = () => {
  createForm.value = {
    name: '',
    description: '',
    chunk_size: 1000,
    chunk_overlap: 200
  }
}

// 编辑知识库（占位）
const editKnowledgeBase = (kb) => {
  message.info('编辑功能开发中...')
}

// 删除知识库
const deleteKb = (kb) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除知识库“${kb.name}”吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      try {
        await kbStore.deleteKnowledgeBase(kb.id)
        message.success('删除成功')
      } catch (err) {
        message.error(err.message || '删除失败')
      }
    }
  })
}

// 上传文件前校验
const beforeUpload = (file) => {
  const allowedMimeTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-word.document.macroEnabled.12',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-powerpoint',
    'text/plain',
    'text/markdown',
    'image/jpeg',
    'image/png',
    'image/gif'
  ]
  const allowedExtensions = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'markdown', 'csv', 'jpg', 'jpeg', 'png', 'gif'
  ]

  const resolvedType = file.type || ''
  const extension = (file.name || '').split('.').pop()?.toLowerCase() || ''
  const isValidType = allowedMimeTypes.includes(resolvedType) || allowedExtensions.includes(extension)

  if (!isValidType) {
    message.error('仅支持 PDF、Word、Excel、PPT、文本、Markdown 以及常见图片格式')
  }

  const isLt100M = file.size / 1024 / 1024 < 100
  if (!isLt100M) {
    message.error('文件大小不能超过 100MB')
  }

  return isValidType && isLt100M
}

// 自定义上传实现
const handleUpload = async (options) => {
  const { file, onProgress, onSuccess, onError } = options
  try {
    await kbStore.uploadFile(
      currentKnowledgeBase.value.id,
      file,
      (percent) => onProgress({ percent })
    )
    onSuccess()
    message.success(`${file.name} 上传成功，正在处理...`)
    // 稍后刷新文件列表（等待后端处理入库）
    setTimeout(() => {
      refreshFiles()
    }, 1000)
  } catch (err) {
    onError(err)
    message.error(`${file.name} 上传失败`)
  }
}

// 设置面板更新后的回调
const handleKbUpdated = (updatedKb) => {
  kbStore.setCurrentKnowledgeBase(updatedKb)
  const index = knowledgeBases.value.findIndex(kb => kb.id === updatedKb.id)
  if (index > -1) knowledgeBases.value[index] = updatedKb
}

// 初始化加载知识库列表
onMounted(async () => {
  await kbStore.fetchKnowledgeBases()
})
</script>

<style scoped>
.knowledge-base-layout {
  display: flex;
  background: #f5f5f5;
  height: 100vh;
}

.kb-sidebar {
  width: 320px;
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
}

.kb-sidebar-header {
  margin-top: 22px;
  padding: 20px;
}

.kb-sidebar-header h2 {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
}

.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.kb-item {
  display: flex;
  align-items: center;
  padding: 16px;
  margin-bottom: 8px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.kb-item:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.kb-item.active {
  border-color: #1890ff;
  background: #f0f7ff;
}

.kb-item-content { flex: 1; }

.kb-item-content h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
}

.description {
  margin: 0 0 8px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.4;
}

.kb-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
}

.kb-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.welcome-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  margin: 16px;
  border-radius: 8px;
}

.kb-content {
  flex: 1;
  background: white;
  margin: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 24px 15px 24px;
  border-bottom: 1px solid #e8e8e8;
}

.kb-info h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.kb-info p { margin: 0; color: #666; font-size: 14px; }

.kb-actions { display: flex; gap: 12px; }

.kb-tabs { flex: 1; padding: 0 24px; }

.form-help { font-size: 12px; color: #999; margin-top: 4px; }

:deep(.ant-tabs-content-holder) {
  height: calc(100vh - 200px);
  overflow-y: auto;
}

/* —— 响应式优化：中小屏将布局纵向堆叠 —— */
@media (max-width: 1200px) {
  .kb-sidebar { width: 280px; }
}

@media (max-width: 992px) {
  .knowledge-base-layout { flex-direction: column; height: auto; min-height: 100dvh; }
  .kb-sidebar { width: 100%; border-right: none; border-bottom: 1px solid #e8e8e8; }
  .kb-list { max-height: 40vh; }
  .kb-main { width: 100%; }
  :deep(.ant-tabs-content-holder) { height: auto; min-height: 60vh; }
}

@media (max-width: 576px) {
  .kb-sidebar-header { padding: 16px; }
  .kb-stats { gap: 10px; }
  .kb-content { margin: 8px; }
}
</style>
