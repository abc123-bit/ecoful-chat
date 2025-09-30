<template>
  <div class="main-chat">
    <!-- 顶部 -->
    <div class="chat-header">
        <h3>{{ conversation ? conversation.title || '新对话' : '新对话' }}</h3>
    </div>

    <!-- 消息区 -->
    <div class="chat-messages" ref="messagesContainer">
      <template v-if="messages.length > 0">
        <Message
        v-for="(m, idx) in messages"
        :key="m.id || idx"
        :message="m"
        :feedback-enabled="feedbackEnabled"
        @like="(id)=>$emit('like-message', id)"
        @dislike="(id)=>$emit('dislike-message', id)"
        @copy="(id)=>$emit('copy-message', id)"
        @edit-message="handleEditMessage"
      />
      </template>

      <div v-else class="empty-state">
        <div class="empty-title">开始新的对话</div>
        <div class="empty-desc">你可以直接输入问题，或上传图片/文件进行辅助说明。</div>
      </div>

      <!-- 回到底部 -->
      <button v-show="showScrollButton" class="scroll-bottom-btn" @click="scrollToBottom" title="回到底部">
        <DownOutlined />
      </button>
    </div>

    <!-- 输入与上传区域（优化 UI） -->
    <div class="chat-input-area">
      <div class="input-shell">
        <!-- 输入框（去除多余边框） -->
        <a-textarea
          v-model:value="inputValue"
          :key="textareaKey"
          :placeholder="isLoading ? '等待回复中...' : '有问题，尽管问，Shift+Enter 换行'"
          :disabled="isLoading"
          :auto-size="{ minRows: 1, maxRows: 6 }"
          class="chat-input"
          @keydown="handleKeyDown"
          ref="textInput"
        />

        <!-- 右侧工具条 -->
        <div class="right-tools">
          <span class="tools-divider" ></span>

          <!-- 上传入口（由能力开关控制） -->
          <template v-if="filesEnabled">
            <!-- 只选图片 -->
            <button class="icon-btn" :disabled="isLoading" @click="triggerImageInput" title="上传图片">
              <FileImageOutlined />
            </button>

            <!-- 只选文件 -->
            <button class="icon-btn" :disabled="isLoading" @click="triggerDocInput" title="上传文件（pdf/word/txt/md/代码等）">
              <FileOutlined />
            </button>
          </template>

          <!-- 发送 / 停止 -->
          <button
            v-if="!isLoading"
            class="send-btn"
            :class="{ 'send-able': inputValue.trim() || uploadedFiles.length>0 }"
            :disabled="!inputValue.trim() && uploadedFiles.length===0"
            @click="handleSend"
            title="发送"
          >
            <SendOutlined />
          </button>
          <button v-else class="stop-btn" @click="$emit('stop-generation')" title="停止生成">
            <StopOutlined />
          </button>
        </div>

        <!-- 单一隐藏 input，根据点击来源切换 accept -->
        <input
          type="file"
          ref="fileInput"
          style="display: none"
          :accept="currentAccept"
          multiple
          @change="handleFileUpload"
        />
      </div>

      <!-- 已上传文件预览 -->
      <div v-if="filesEnabled && uploadedFiles.length > 0" class="uploaded-files">
        <div v-for="(file, index) in uploadedFiles" :key="index" class="file-item">
          <span class="file-name">
            <FileImageOutlined v-if="isImage(file)" />
            <FileOutlined v-else />
            {{ file.name }}
          </span>
          <button class="remove-file-btn" @click="removeFile(index)" title="移除文件">
            <CloseOutlined />
          </button>
        </div>
      </div>

      <!-- 说明文字 -->
      <div class="constraints-hint" v-if="filesEnabled">
        单次仅能选择 <strong>图片或文件其中一种</strong>；最多 <strong>10</strong> 个；已选附件不可重复。Enter 发送，Shift+Enter 换行
      </div>

      <!-- 计数 -->
      <div class="input-footer" v-if="conversation">
        <span class="message-count">{{ messages.length }} 条消息</span>
        <span v-if="filesEnabled && uploadedFiles.length > 0" class="file-count">｜{{ uploadedFiles.length }} 个附件</span>
      </div>
    </div>

    <!-- 轻量 Toast（自动消失） -->
    <transition name="toast">
      <div class="toast" v-if="toast.visible">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
/**
 * - UI：单层超圆角容器、无双边框、右侧小方按钮 + 圆形发送
 * - 行为：点击图片=仅 image/*；点击文件=仅非图片（pdf/word/txt/md/代码等）
 * - 规则：不得混传；上限10；去重；与历史类型一致；Toast 短暂提示
 * - 交互：Enter 发送，Shift+Enter 换行（保持）
 */
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { 
  MenuOutlined, 
  SendOutlined, 
  StopOutlined, 
  DownOutlined,
  FileOutlined,
  FileImageOutlined,
  CloseOutlined
} from '@ant-design/icons-vue'
import Message from './Message.vue'

const props = defineProps({
  conversation: { type: Object, default: null },
  messages: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false },
  error: { type: String, default: null },
  isSidebarCollapsed: { type: Boolean, default: false },
  // 是否启用文件上传（由 Provider 能力控制）
  filesEnabled: { type: Boolean, default: true },
  // 是否启用点赞/点踩（由 Provider 能力控制）
  feedbackEnabled: { type: Boolean, default: true }
})

const emit = defineEmits([
  'send-message', 'stop-generation', 'toggle-sidebar', 'toggle-desktop-sidebar',
  'like-message', 'dislike-message', 'copy-message', 'clear-error', 'upload-files', 'edit-message'
])

/* 输入/滚动 */
const inputValue = ref('')
const messagesContainer = ref(null)
const isUserScrolling = ref(false)
const lastScrollTop = ref(0)
const showScrollButton = ref(false)

const textareaKey = ref(0)
const textInput = ref(null)

/* 上传：两个入口切 accept */
const fileInput = ref(null)
const uploadedFiles = ref([])
const uploadKind = ref(null) // 'image' | 'file' | null
const IMAGE_ACCEPT = 'image/*'

// 常见办公/文本/代码文件（不含图片）
const FILE_ACCEPT = [
  '.pdf','.doc','.docx','.ppt','.pptx','.xls','.xlsx',
  '.txt','.md','.rtf','.csv','.json','.xml',
  '.html','.htm','.css','.scss',
  '.js','.ts','.jsx','.tsx','.vue',
  '.java','.py','.cpp','.c','.cs','.go','.rb','.php','.rs','.kt','.swift',
  '.sh','.bat','.ps1',
  '.sql','.ini','.conf','.yml','.yaml','.log'
].join(',')
const currentAccept = ref(IMAGE_ACCEPT) // 默认随点击动态切换

/* Toast */
const toast = ref({ visible: false, message: '' })
let toastTimer = null
const showToast = (msg, ms = 2200) => {
  toast.value.message = msg
  toast.value.visible = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value.visible = false), ms)
}

/* 滚动 */
const scrollToBottom = () => {
  nextTick(() => {
    if (!messagesContainer.value) return
    const c = messagesContainer.value
    c.scrollTop = c.scrollHeight
    showScrollButton.value = false
  })
}
const isNearBottom = () => {
  if (!messagesContainer.value) return true
  const c = messagesContainer.value
  const threshold = 100
  return c.scrollTop + c.clientHeight >= c.scrollHeight - threshold
}
const updateScrollButton = () => { showScrollButton.value = !isNearBottom() && props.messages.length > 0 }
const handleScroll = () => {
  if (!messagesContainer.value) return
  const current = messagesContainer.value.scrollTop
  if (current < lastScrollTop.value || !isNearBottom()) isUserScrolling.value = true
  else if (isNearBottom()) isUserScrolling.value = false
  lastScrollTop.value = current
  updateScrollButton()
}
const resetScrollState = () => { isUserScrolling.value = false; scrollToBottom() }
watch(() => props.messages.length, () => resetScrollState())
watch(() => (props.messages.length > 0 ? props.messages[props.messages.length - 1].content : ''), () => debounceSmartScroll())
watch(() => props.isLoading, (n) => { if (n) resetScrollState() })
onMounted(() => { if (messagesContainer.value) messagesContainer.value.addEventListener('scroll', handleScroll, { passive: true }) })
onUnmounted(() => { if (messagesContainer.value) messagesContainer.value.removeEventListener('scroll', handleScroll) })
let timer = null
const debounceSmartScroll = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => { if (!isUserScrolling.value) scrollToBottom() }, 150)
}

/* 发送/编辑 */
const handleSend = () => {
  if ((inputValue.value.trim() || uploadedFiles.value.length > 0) && !props.isLoading) {
    const content = inputValue.value.trim()
    emit('send-message', content, uploadedFiles.value)
    inputValue.value = ''
    uploadedFiles.value = []
    uploadKind.value = null
    textareaKey.value++
    nextTick(() => { if (textInput.value) textInput.value.focus() })
  }
}

// 回车发送消息
const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }

// 编辑消息（将内容放入主输入框）
const handleEditMessage = (messageData) => {
  inputValue.value = messageData.content || ''
  
  if (messageData.files && messageData.files.length > 0) {
    uploadedFiles.value = [...messageData.files]
    if (messageData.files[0].type.startsWith('image/')) {
      uploadKind.value = 'image'
    } else {
      uploadKind.value = 'file'
    }
  } else {
    uploadedFiles.value = []
    uploadKind.value = null
  }
  
  textareaKey.value++
  nextTick(() => {
    if (textInput.value) {
      textInput.value.focus()
      const textareaDom = textInput.value.$el?.querySelector?.('textarea')
      if (textareaDom) {
        textareaDom.select()
      }
    }
  })
}

/* 触发上传（严格区分两类） */
const triggerImageInput = () => {
  if (!props.filesEnabled) return
  currentAccept.value = IMAGE_ACCEPT
  if (fileInput.value) fileInput.value.click()
}
const triggerDocInput = () => {
  if (!props.filesEnabled) return
  currentAccept.value = FILE_ACCEPT
  if (fileInput.value) fileInput.value.click()
}

/* 工具：扩展名判断（用于防呆） */
const getExt = (name='') => {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}
const isImage = (file) => file.type.startsWith('image/')

/* 文件上传校验 */
const handleFileUpload = (e) => {
  if (!props.filesEnabled) { e.target.value = ''
    return }
  const selected = Array.from(e.target.files || [])
  if (!selected.length) return

  // 入口限定：根据 currentAccept 再做一次类型兜底校验
  const isImageMode = currentAccept.value === IMAGE_ACCEPT
  const acceptedExts = new Set(currentAccept.value.split(',').map(s=>s.trim()).filter(Boolean))

  const byAccept = selected.filter(f => {
    if (isImageMode) return f.type.startsWith('image/')
    // 非图片：若有 MIME 则按 非 image；无 MIME 则按扩展名
    if (f.type) return !f.type.startsWith('image/')
    return acceptedExts.has(getExt(f.name))
  })

  if (byAccept.length !== selected.length) {
    showToast(isImageMode ? '已过滤非图片文件' : '已过滤不支持的文件类型')
  }

  // 与历史类型一致
  const chosenKind = isImageMode ? 'image' : 'file'
  if (uploadKind.value && uploadKind.value !== chosenKind) {
    showToast('当前已选择了另一种类型的附件，请先清空或移除后再上传')
    e.target.value = ''
    return
  }

  // 去重（name+size）
  const key = (f) => `${f.name}__${f.size}`
  const existingKeys = new Set(uploadedFiles.value.map(key))
  const deduped = byAccept.filter(f => !existingKeys.has(key(f)))
  if (deduped.length !== byAccept.length) {
    showToast('已忽略重复的文件/图片')
  }

  // 禁止“混传”（本次选择里混入另一类）
  if (!isImageMode && deduped.some(ff => ff.type.startsWith('image/'))) {
    showToast('一次只能选择图片或文件其中一种，请分批上传')
    e.target.value = ''
    return
  }
  if (isImageMode && deduped.some(ff => !ff.type.startsWith('image/'))) {
    showToast('一次只能选择图片或文件其中一种，请分批上传')
    e.target.value = ''
    return
  }

  // 数量上限
  const allowedCount = Math.max(0, 10 - uploadedFiles.value.length)
  if (allowedCount <= 0) {
    showToast('最多只能上传 10 个附件')
    e.target.value = ''
    return
  }

  const nextBatch = deduped.slice(0, allowedCount)
  if (deduped.length > allowedCount) {
    showToast(`已达到数量上限，超出的 ${deduped.length - allowedCount} 个未添加`)
  }

  uploadedFiles.value = [...uploadedFiles.value, ...nextBatch]
  emit('upload-files', nextBatch)
  e.target.value = ''
  uploadKind.value = chosenKind
}

/* 其它 */
const removeFile = (index) => { 
  uploadedFiles.value.splice(index, 1)
  if (uploadedFiles.value.length===0) uploadKind.value=null 
}
</script>

<style scoped>
/* —— 顶部 —— */
.chat-header { height: 60px; border-bottom: 1px solid #e8e8e8; display: flex; align-items: center; padding: 0 20px; background: #fff; }
.chat-header h3 { margin: 0; font-size: 18px; font-weight: 600; color: #1f2328; }
.desktop-expand-btn { display: none; background: #fff; border: 1px solid #e5e7eb; cursor: pointer; color: #666; font-size: 16px; margin-right: 12px; padding: 8px; border-radius: 6px; transition: all .2s; }
.desktop-expand-btn:hover { background: #f5f5f5; color: #1890ff; }
.mobile-menu-btn { display: none; background: none; border: none; cursor: pointer; color: #666; font-size: 18px; margin-right: 12px; }
@media (min-width: 769px) { .desktop-expand-btn { display: block; } }
@media (max-width: 768px) { .mobile-menu-btn { display: block; } .desktop-expand-btn { display: none; } .chat-header h3 { font-size: 16px; } }

/* —— 消息区 —— */
.chat-messages { flex: 1; overflow-y: auto; padding: 20px; background: #fff; scroll-behavior: smooth; }
.empty-state { margin: 48px auto; text-align: center; color: #6b7280; }
.empty-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; color: #111827; }
.empty-desc { font-size: 13px; }

/* 回到底部按钮 */
.scroll-bottom-btn { position: sticky; bottom: 8px; margin-left: auto; display: inline-flex; align-items: center; justify-content: center; background: #5B82EF; color: #fff; border: none; border-radius: 999px; width: 40px; height: 40px; cursor: pointer; box-shadow: 0 6px 16px rgba(0,0,0,.15); }
.scroll-bottom-btn:hover { background: #000; }

/* —— 输入区 —— */
.chat-input-area { border-top: 1px solid #eee; padding: 16px; background: #fafafa; }

/* 单层圆角容器：避免出现“内外两层边框” */
.input-shell {
  position: relative;
  
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  border: 1px solid #e7e9ee;
  background: #fff;
  border-radius: 18px;
  padding: 8px 10px 8px 12px;
  transition: box-shadow .2s, border-color .2s;
}
.input-shell:focus-within {
  border-color: #cfe0ff;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}

/* 去掉 antd textarea 自带边框/阴影（关键：提升选择器优先级） */
.input-shell :deep(.ant-input),
.input-shell :deep(textarea.ant-input),
.input-shell :deep(.ant-input:focus),
.input-shell :deep(.ant-input-focused),
.chat-input :deep(textarea) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

.chat-input :deep(textarea) {
  padding: 6px 8px;
  resize: none;
  font-size: 14px;
  line-height: 1.6;
}
.chat-input :deep(textarea::placeholder) { color: #b5b8c0; }

/* 右侧工具组 */
.right-tools {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding-right: 6px;
}
.tools-divider {
  display: inline-block;
  width: 1px;
  height: 22px;
  background: #eceef2;
  margin-right: 2px;
}

/* 小方按钮（圆角 10） */
.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e6e7eb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all .12s;
  color: #4b5563;
}
.icon-btn:hover { transform: translateY(-1px); border-color: #c7d2fe; }
.icon-btn:disabled { opacity: .5; cursor: not-allowed; }

/* 发送 & 停止：圆形 */
.send-btn, .stop-btn {
  width: 50px;
  height: 50px;
  border-radius: 999px;
  border: 1px solid #e6e7eb;
  background: #f3f4f6;
  color: #9aa0a6;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all .15s;
  margin-right: 2%;
}
.send-btn.send-able {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}
.send-btn:not(.send-able) { cursor: not-allowed; }
.send-btn.send-able:hover { background: #2563eb; border-color: #2563eb; }
.stop-btn { background: #ef4444; border-color: #ef4444; color: #fff; }
.stop-btn:hover { background: #dc2626; border-color: #dc2626; }

/* 已上传预览：胶囊 */
.uploaded-files { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
.file-item { display: flex; align-items: center; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 999px; padding: 6px 10px; font-size: 13px; }
.file-name { display: flex; align-items: center; gap: 6px; margin-right: 2px; color: #374151; }
.remove-file-btn { background: none; border: none; color: #9ca3af; cursor: pointer; padding: 2px; border-radius: 4px; margin-left: 6px; }
.remove-file-btn:hover { color: #ef4444; background-color: #fee2e2; }

/* 说明/计数 */
.constraints-hint { margin-top: 8px; font-size: 12px; color: #8e8ea0; }
.input-footer { margin-top: 4px; font-size: 12px; color: #8e8ea0; }
.file-count { margin-left: 6px; }

/* Toast */
.toast {
  position: fixed;
  right: 18px;
  bottom: 88px;
  max-width: 70vw;
  background: #111827;
  color: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0,0,0,.18);
  font-size: 13px;
  z-index: 50;
}
.toast-enter-active, .toast-leave-active { transition: all .18s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(6px); }

/* —— 响应式：根据屏幕收敛留白与尺寸 —— */
@media (max-width: 1200px) {
  .chat-messages { padding: 16px; }
}

@media (max-width: 992px) {
  .chat-messages { padding: 12px; }
  .icon-btn { width: 32px; height: 32px; }
  .send-btn, .stop-btn { width: 46px; height: 46px; }
}

@media (max-width: 768px) {
  .chat-input-area { padding: 12px; }
  .input-shell { padding: 6px 8px; border-radius: 14px; }
  .chat-header { height: 56px; }
  .chat-messages { padding: 10px; }
  .send-btn, .stop-btn { width: 42px; height: 42px; }
}

@media (max-width: 576px) {
  .empty-title { font-size: 15px; }
  .empty-desc { font-size: 12px; }
  .chat-input :deep(textarea) { font-size: 13px; }
}
</style>
