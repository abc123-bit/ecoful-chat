<template>
  <div class="file-manager">
    <div class="file-list">
      <a-table
        :dataSource="files"
        :columns="columns"
        :loading="isLoading"
        :pagination="false"
        :scroll="{ y: 400 }"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'filename'">
            <div class="file-info">
              <FileOutlined />
              <span>{{ record.filename }}</span>
            </div>
          </template>

          <template v-if="column.key === 'status'">
            <a-tag
              :color="getStatusColor(record.processing_status)"
            >
              {{ getStatusText(record.processing_status) }}
            </a-tag>
          </template>

          <template v-if="column.key === 'size'">
            {{ formatFileSize(record.file_size) }}
          </template>

          <template v-if="column.key === 'created_at'">
            {{ formatTime(record.created_at) }}
          </template>

          <template v-if="column.key === 'actions'">
            <a-button
              type="text"
              size="small"
              @click="viewFile(record)"
              :disabled="record.processing_status !== 'completed'"
            >
              查看
            </a-button>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 文件详情模态框 -->
    <a-modal
      v-model:open="showFileModal"
      :title="selectedFile?.filename"
      width="800px"
      :footer="null"
    >
      <div v-if="selectedFile">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="文件大小">
            {{ formatFileSize(selectedFile.file_size) }}
          </a-descriptions-item>
          <a-descriptions-item label="文件类型">
            {{ selectedFile.file_type }}
          </a-descriptions-item>
          <a-descriptions-item label="处理状态">
            <a-tag :color="getStatusColor(selectedFile.processing_status)">
              {{ getStatusText(selectedFile.processing_status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="文档块数">
            {{ selectedFile.chunk_count || 0 }}
          </a-descriptions-item>
        </a-descriptions>

        <div v-if="selectedFile.extracted_text" class="file-content">
          <h4>提取的文本内容：</h4>
          <div class="text-content">
            {{ selectedFile.extracted_text }}
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { FileOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'

const props = defineProps({
  knowledgeBase: Object,
  files: Array
})

const emit = defineEmits(['refresh'])

const showFileModal = ref(false)
const selectedFile = ref(null)
const isLoading = ref(false)

const columns = [
  {
    title: '文件名',
    key: 'filename',
    dataIndex: 'filename',
    ellipsis: true
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'processing_status',
    width: 100
  },
  {
    title: '大小',
    key: 'size',
    dataIndex: 'file_size',
    width: 100
  },
  {
    title: '上传时间',
    key: 'created_at',
    dataIndex: 'created_at',
    width: 160
  },
  {
    title: '操作',
    key: 'actions',
    width: 80
  }
]

const getStatusColor = (status) => {
  const colors = {
    pending: 'orange',
    processing: 'blue',
    completed: 'green',
    failed: 'red'
  }
  return colors[status] || 'default'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

const viewFile = (file) => {
  selectedFile.value = file
  showFileModal.value = true
}
</script>

<style scoped>
.file-manager {
  padding: 16px 0;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-content {
  margin-top: 16px;
}

.file-content h4 {
  margin: 0 0 12px 0;
}

.text-content {
  max-height: 300px;
  overflow-y: auto;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>