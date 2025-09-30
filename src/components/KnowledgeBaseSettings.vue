<template>
  <div class="kb-settings">
    <a-form :model="form" layout="vertical" @finish="handleSubmit">
      <a-form-item label="知识库名称" required>
        <a-input
          v-model:value="form.name"
          placeholder="请输入知识库名称"
          :maxlength="255"
          show-count
        />
      </a-form-item>

      <a-form-item label="描述">
        <a-textarea
          v-model:value="form.description"
          placeholder="请输入知识库描述"
          :rows="3"
          :maxlength="1000"
          show-count
        />
      </a-form-item>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="分块大小">
            <a-input-number
              v-model:value="form.chunk_size"
              :min="100"
              :max="4000"
              style="width: 100%"
            />
            <div class="form-help">建议1000-2000字符</div>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="重叠大小">
            <a-input-number
              v-model:value="form.chunk_overlap"
              :min="0"
              :max="1000"
              style="width: 100%"
            />
            <div class="form-help">建议100-300字符</div>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item>
        <a-button type="primary" html-type="submit" :loading="isLoading">
          保存设置
        </a-button>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { message } from 'ant-design-vue'
import knowledgeBaseService from '@/services/knowledgeBase'

const props = defineProps({
  knowledgeBase: Object
})

const emit = defineEmits(['updated'])

const isLoading = ref(false)
const form = reactive({
  name: '',
  description: '',
  chunk_size: 1000,
  chunk_overlap: 200
})

// 监听知识库变化，更新表单
watch(() => props.knowledgeBase, (kb) => {
  if (kb) {
    form.name = kb.name
    form.description = kb.description || ''
    form.chunk_size = kb.chunk_size
    form.chunk_overlap = kb.chunk_overlap
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!form.name.trim()) {
    message.error('请输入知识库名称')
    return
  }

  try {
    isLoading.value = true
    const updated = await knowledgeBaseService.updateKnowledgeBase(
      props.knowledgeBase.id,
      form
    )
    emit('updated', updated)
    message.success('设置已保存')
  } catch (error) {
    message.error(error.message || '保存失败')
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.kb-settings {
  padding: 16px 0;
  max-width: 600px;
}

.form-help {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>