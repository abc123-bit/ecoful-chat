<template>
  <!-- UTF-8：统一聊天页面（可切换 Provider，默认 RAG） -->
  <div class="u-layout">
    <!-- 左侧：统一会话侧栏 -->
    <UnifiedSidebar
      :provider="provider"
      :conversations="conversations"
      :current-id="currentConv?.id || ''"
      :loading="loading.conversations"
      @refresh="loadConversations"
      @select="handleSelectConversation"
      @delete="handleDeleteConversation"
      @new-conversation="startNewConversation"
    />

    <!-- 右侧：聊天区域 -->
    <div class="u-main">
      <div class="u-topbar">
        <div class="left">
          <a-segmented v-model:value="state.providerId" :options="providerOptions" @change="onProviderChange" />
          <!-- RAG 需要知识库选择器 -->
          <div v-if="state.providerId==='rag'" class="kb-slot">
            <a-select v-model:value="state.kbId" :options="kbOptions" placeholder="选择知识库" style="min-width:220px" @change="onKbChange" />
          </div>
        </div>
        <div class="right">
          <a-tag v-if="provider?.id" color="blue">{{ provider?.name }}</a-tag>
          <template v-if="provider?.capabilities?.sources">
            <a-button type="text" :disabled="!(latestSources && latestSources.length)" @click="openSources" aria-label="打开参考来源">
              参考来源
            </a-button>
          </template>
        </div>
      </div>

      <!-- 复用既有 MainChat 组件，保持现有交互体验 -->
      <MainChat
        :conversation="currentConv"
        :messages="messages"
        :is-loading="loading.stream || loading.messages"
        :error="error"
        :is-sidebar-collapsed="false"
        :files-enabled="!!(provider?.capabilities?.files?.enabled)"
        :feedback-enabled="!!(provider?.capabilities?.feedback)"
        @send-message="handleSend"
        @stop-generation="handleStop"
        @like-message="handleLike"
        @dislike-message="handleDislike"
        @copy-message="handleCopy"
      />

      <!-- 来源预览面板（仅当 Provider 支持来源时有效） -->
      <SourcesPreviewPane :visible="sourcesVisible" :sources="sourcesData" @close="sourcesVisible=false" />
    </div>
  </div>
</template>

<script setup>
// 说明：新增统一聊天入口，不改动现有页面与逻辑，作为增量功能
import { reactive, ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { v4 as uuidv4 } from 'uuid'
import UnifiedSidebar from '@/components/UnifiedSidebar.vue'
import MainChat from '@/components/MainChat.vue'
import SourcesPreviewPane from '@/components/SourcesPreviewPane.vue'
import { providers, getProviderById } from '@/providers/registry'
import KnowledgeBaseService from '@/services/knowledgeBase'
import difyService from '@/services/dify'
import { copyToClipboard } from '@/utils/helpers'

// 页面状态
const route = useRoute()
const router = useRouter()
const state = reactive({
  providerId: 'rag',   // 默认 RAG（可被路由参数覆盖）
  kbId: null,          // RAG 所需
  maxChunks: 6,
})

// Provider 选项
const providerOptions = providers.map(p => ({ label: p.name, value: p.id }))
const provider = computed(() => getProviderById(state.providerId))
const agentId = computed(() => route.query?.agent ? String(route.query.agent) : null)
const kbFromQuery = computed(() => route.query?.kb ? Number(route.query.kb) : null)
const conversationFromQuery = computed(() => route.query?.conversation ? String(route.query.conversation) : null)

// 会话/消息/加载
const conversations = ref([])
const currentConv = ref(null)
const messages = ref([])
const error = ref(null)
const loading = reactive({ conversations: false, messages: false, stream: false })
let abortController = null

function ensureConversationRegistered(conversation) {
  if (!conversation?.id) return
  const idx = conversations.value.findIndex(item => item.id === conversation.id)
  const entry = { ...conversation }
  if (idx === -1) {
    conversations.value = [entry, ...conversations.value]
  } else {
    const merged = { ...conversations.value[idx], ...entry }
    conversations.value.splice(idx, 1)
    conversations.value.unshift(merged)
  }
}

function patchConversationById(id, patch, { moveToTop = false } = {}) {
  if (!id) return
  if (currentConv.value && currentConv.value.id === id) {
    currentConv.value = { ...currentConv.value, ...patch }
  }
  const idx = conversations.value.findIndex(item => item.id === id)
  if (idx !== -1) {
    const updated = { ...conversations.value[idx], ...patch }
    conversations.value.splice(idx, 1)
    if (moveToTop) {
      conversations.value.unshift(updated)
    } else {
      conversations.value.splice(idx, 0, updated)
    }
  } else if (patch && Object.keys(patch).length) {
    const entry = { id, ...patch }
    if (moveToTop) {
      conversations.value = [entry, ...conversations.value]
    } else {
      conversations.value = [...conversations.value, entry]
    }
  }
}

function remapConversationId(oldId, newId, extraPatch = {}) {
  if (!oldId || !newId || oldId === newId) return
  const patch = { ...extraPatch }
  if (currentConv.value && currentConv.value.id === oldId) {
    currentConv.value = { ...currentConv.value, id: newId, ...patch }
  }
  const existingNewIdx = conversations.value.findIndex(item => item.id === newId)
  if (existingNewIdx !== -1) {
    conversations.value.splice(existingNewIdx, 1)
  }
  const idx = conversations.value.findIndex(item => item.id === oldId)
  if (idx !== -1) {
    const updated = { ...conversations.value[idx], ...patch, id: newId }
    conversations.value.splice(idx, 1)
    conversations.value.unshift(updated)
  } else {
    conversations.value = [{ id: newId, ...patch }, ...conversations.value]
  }
}

// 参考来源预览：最后一条助手消息的来源
const sourcesVisible = ref(false)
const sourcesData = ref([])
const latestSources = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m?.role === 'assistant' && Array.isArray(m.sources) && m.sources.length) return m.sources
  }
  return []
})

// RAG 知识库下拉
const kbOptions = ref([])
async function initKbOptions(){
  try{
    const list = await KnowledgeBaseService.getKnowledgeBases()
    kbOptions.value = (list||[]).map(k=>({label:k.name, value:k.id}))
    if(kbFromQuery.value && kbOptions.value.some(o => o.value === kbFromQuery.value)){
      state.kbId = kbFromQuery.value
    } else if(!state.kbId && kbOptions.value.length){
      state.kbId = kbOptions.value[0].value
    }
  }catch{ /* 忽略 */ }
}

function buildProviderContext(){
  if(state.providerId==='rag'){
    return { kbId: state.kbId, maxChunks: state.maxChunks }
  }
  if(state.providerId==='dify'){
    return { agentId: agentId.value || null }
  }
  return {}
}

// 加载会话
async function loadConversations(){
  try{
    loading.conversations = true
    if(!provider.value){
      conversations.value = []
      return []
    }
    if(state.providerId==='rag' && !state.kbId){
      conversations.value = []
      return []
    }
    const ctx = buildProviderContext()
    const list = await provider.value.listConversations?.(ctx) || []
    const normalized = list.map(item => {
      const created = item.createdAt instanceof Date ? item.createdAt : new Date(item.createdAt)
      const updated = item.updatedAt instanceof Date ? item.updatedAt : new Date(item.updatedAt)
      return {
        ...item,
        createdAt: Number.isNaN(created.getTime()) ? new Date() : created,
        updatedAt: Number.isNaN(updated.getTime()) ? new Date() : updated,
      }
    }).sort((a, b) => {
      const aTime = a.updatedAt ? a.updatedAt.getTime() : 0
      const bTime = b.updatedAt ? b.updatedAt.getTime() : 0
      return bTime - aTime
    })
    conversations.value = normalized
    return normalized
  }catch(e){ message.error('加载会话失败'); return [] }
  finally{ loading.conversations = false }
}

function focusLatestConversation(list){
  const source = Array.isArray(list) && list.length ? list : conversations.value
  if(!source || !source.length){
    if(currentConv.value?.provider === state.providerId && !loading.stream){
      currentConv.value = null
      messages.value = []
    }
    return null
  }
  const latest = source[0]
  if(currentConv.value?.id === latest.id){
    return handleSelectConversation(latest)
  }
  currentConv.value = latest
  return handleSelectConversation(latest)
}

// 选择会话
async function handleSelectConversation(conv){
  currentConv.value = conv
  await loadMessages(conv)
}

// 加载消息
async function loadMessages(conv){
  if(!conv) return
  try{
    loading.messages = true
    const ctx = buildProviderContext()
    const raw = await provider.value.getMessages?.(conv.providerConvId, ctx) || []
    messages.value = raw.map(item => {
      const ts = item.timestamp instanceof Date
        ? item.timestamp
        : (item.timestamp ? new Date(item.timestamp) : new Date())
      return { ...item, timestamp: Number.isNaN(ts.getTime()) ? new Date() : ts }
    })
    await nextTick()
  }catch(e){ message.error('加载消息失败') }
  finally{ loading.messages = false }
}

// 新建空会话（本地占位）
function startNewConversation(){
  const baseId = state.providerId ? (state.providerId + '_') : 'local_'
  const id = baseId + uuidv4()
  const conv = {
    id,
    title: '新的对话',
    createdAt: new Date(),
    updatedAt: new Date(),
    provider: state.providerId,
    providerConvId: null,
  }
  currentConv.value = conv
  ensureConversationRegistered(conv)
  messages.value = []
}

// 删除会话
async function handleDeleteConversation(conv){
  try{
    const ctx = buildProviderContext()
    await provider.value.deleteConversation?.(conv.providerConvId, ctx)
    await loadConversations()
    if(currentConv.value?.id === conv.id){
      currentConv.value = null
      messages.value = []
    }
    message.success('已删除')
  }catch{ message.error('删除失败') }
}

// 发送消息（统一流式）
async function handleSend(content, files = []){
  if(!content && (!files || files.length===0)) return
  const prov = provider.value
  const ctx = buildProviderContext()

  const trimmedContent = (content || '').trim()
  const snippetTitle = trimmedContent
    ? (trimmedContent.length > 36 ? trimmedContent.slice(0, 36) + '...' : trimmedContent)
    : '新的对话'

  if (!currentConv.value) {
    // 首次提问时还没有会话，先创建一个本地占位会话，便于左侧立即展示
    const prefix = prov?.id || state.providerId || 'conversation'
    const tempConv = {
      id: `${prefix}_temp_${uuidv4()}`,
      title: snippetTitle,
      createdAt: new Date(),
      updatedAt: new Date(),
      provider: prefix,
      providerConvId: null,
      isPending: true,
    }
    currentConv.value = tempConv
    ensureConversationRegistered(tempConv)
  } else {
    ensureConversationRegistered(currentConv.value)
  }

  const conv = currentConv.value

  messages.value.push({
    id: uuidv4(),
    role: 'user',
    content,
    files,
    provider: prov?.id,
    timestamp: new Date()
  })
  const aiMsg = {
    id: uuidv4(),
    role: 'assistant',
    content: '',
    provider: prov?.id,
    timestamp: new Date(),
    isStreaming: true
  }
  messages.value.push(aiMsg)
  const aiIndex = messages.value.length - 1

  if (conv?.id) {
    const patch = { updatedAt: new Date() }
    if (!conv.createdAt) patch.createdAt = new Date()
    if (trimmedContent && (!conv.title || conv.title === '新的对话')) {
      patch.title = snippetTitle
    }
    patchConversationById(conv.id, patch, { moveToTop: true })
  }

  const patchAssistantMessage = (updates = {}) => {
    if (aiIndex < 0) return
    const prev = messages.value[aiIndex]
    if (!prev) return
    messages.value.splice(aiIndex, 1, {
      ...prev,
      ...updates
    })
  }

  loading.stream = true
  abortController = new AbortController()
  const overwriteStream = prov?.id === 'dify'

  try{
    await prov.sendMessage({
      content,
      files,
      providerConvId: currentConv.value?.providerConvId || null,
      context: ctx,
      onEvent: (evt)=>{
        const activeId = currentConv.value?.id
        if((evt?.type==='start' || evt?.type==='content') && evt?.conversationId && activeId){
          const prefix = prov?.id || state.providerId || 'conversation'
          const serverId = `${prefix}_${evt.conversationId}`
          const patch = {
            providerConvId: evt.conversationId,
            updatedAt: new Date(),
            isPending: false,
          }
          if (trimmedContent && (!currentConv.value?.title || currentConv.value.title === '新的对话')) {
            patch.title = snippetTitle
          }
          if (!currentConv.value?.createdAt) {
            patch.createdAt = new Date()
          }
          if (activeId !== serverId) {
            remapConversationId(activeId, serverId, patch)
          } else {
            patchConversationById(activeId, patch, { moveToTop: true })
          }
        }
        if(evt?.type==='content' && typeof evt.content==='string'){
          const prevContent = messages.value[aiIndex]?.content || ''
          const nextContent = overwriteStream ? evt.content : (prevContent + evt.content)
          patchAssistantMessage({
            content: nextContent,
            timestamp: new Date(),
            messageId: evt.messageId || messages.value[aiIndex]?.messageId,
            isStreaming: false
          })
        } else if(evt?.type==='end'){
          const updates = {
            timestamp: new Date(),
            messageId: evt.messageId || messages.value[aiIndex]?.messageId,
            isStreaming: false
          }
          if(typeof evt.content==='string'){
            const prevContent = messages.value[aiIndex]?.content || ''
            updates.content = overwriteStream ? evt.content : (prevContent + evt.content)
          }
          if(Array.isArray(evt.sources) && evt.sources.length){
            updates.sources = evt.sources
          }
          patchAssistantMessage(updates)
          if (currentConv.value?.id) {
            patchConversationById(currentConv.value.id, { updatedAt: new Date() }, { moveToTop: true })
          }
          loading.stream = false
          abortController = null
        }
      },
      abortController,
    })
 }catch(e){
    if(String(e).includes('停止') || String(e).includes('Abort')){ message.info('已停止生成') }
    else { message.error('发送失败，请重试') }
    patchAssistantMessage({ isStreaming: false })
  }finally{
    loading.stream = false
    abortController = null
  }
}


// 停止生成
function handleStop(){
  if(abortController){ abortController.abort(); abortController = null; loading.stream = false }
}

// 反馈（按能力开关调用）
async function handleLike(messageId){
  const prov = provider.value
  if(!prov.capabilities.feedback) return
  try{ await prov.feedback(messageId,'like','', buildProviderContext()) }catch{}
}
async function handleDislike(messageId){
  const prov = provider.value
  if(!prov.capabilities.feedback) return
  try{ await prov.feedback(messageId,'dislike','', buildProviderContext()) }catch{}
}

// 复制
async function handleCopy(content){
  const ok = await copyToClipboard(content)
  ok ? message.success('已复制') : message.error('复制失败')
}

// Provider 切换
async function onProviderChange(){
  const query = { ...route.query }
  if(state.providerId === 'rag'){
    if(state.kbId) query.kb = state.kbId
    delete query.agent
  }else if(state.providerId === 'dify'){
    if(agentId.value) query.agent = agentId.value
    delete query.kb
  }
  if(query.conversation && state.providerId !== 'dify'){
    delete query.conversation
  }
  Object.keys(query).forEach(key => query[key] === undefined && delete query[key])
  router.replace({ name: 'ChatHub', params: { provider: state.providerId }, query })
}

async function onKbChange(){
  const query = { ...route.query, kb: state.kbId || undefined }
  Object.keys(query).forEach(key => query[key] === undefined && delete query[key])
  router.replace({ name: 'ChatHub', params: { provider: 'rag' }, query })
  const list = await loadConversations()
  await focusLatestConversation(list)
}

// 打开参考来源预览
async function openSources(){
  if (!provider.value?.capabilities?.sources) return
  const src = latestSources.value || []
  try{
    sourcesData.value = await KnowledgeBaseService.enrichSourcesWithUrls(src)
  }catch{
    sourcesData.value = src
  }
  sourcesVisible.value = true
}

async function syncFromRoute(){
  let next = route.params?.provider ? String(route.params.provider) : null
  if(next && !getProviderById(next)) next = null
  if(!next && route.meta?.provider && getProviderById(route.meta.provider)){
    next = route.meta.provider
  }
  if(!next) next = state.providerId || 'rag'
  const changed = state.providerId !== next
  state.providerId = next
  if(changed){
    currentConv.value = null
    messages.value = []
  }
  if(state.providerId === 'rag'){
    await initKbOptions()
  }else if(state.providerId === 'dify'){
    try{ difyService.applyAgent(agentId.value || null) }catch(e){ console.warn('应用智能体配置失败', e) }
  }
  const list = await loadConversations()
  if(conversationFromQuery.value){
    const match = (list || conversations.value).find(c => c.providerConvId === conversationFromQuery.value || c.id === conversationFromQuery.value)
    if(match){
      await handleSelectConversation(match)
      return
    }
  }
  if(!currentConv.value || currentConv.value.provider !== state.providerId){
    await focusLatestConversation(list)
  }
}

onMounted(async ()=>{
  await syncFromRoute()
})

watch(() => route.params.provider, syncFromRoute)

watch(agentId, async (val, old) => {
  if(state.providerId !== 'dify') return
  if(val === old) return
  try{ difyService.applyAgent(val || null) }catch(e){ console.warn('切换智能体失败', e) }
  const list = await loadConversations()
  await focusLatestConversation(list)
})

watch(() => kbFromQuery.value, async (val, old) => {
  if(state.providerId !== 'rag') return
  if(val === old || !val) return
  state.kbId = val
  const list = await loadConversations()
  await focusLatestConversation(list)
})
</script>

<style scoped>
.u-layout{ display:flex; height:100vh; background: linear-gradient(135deg, #f7f9fc 0%, #f1f5f9 100%); }
.u-main{ flex:1; min-width:0; display:flex; flex-direction:column; }
.u-topbar{ height:64px; display:flex; align-items:center; justify-content:space-between; padding:0 16px; background:#fff; border-bottom:1px solid #eaecef; position:sticky; top:0; z-index:2; }
.left{ display:flex; align-items:center; gap:12px; }
.kb-slot{ margin-left:8px; }

/* 细腻小过渡 */
.u-main :deep(.ant-segmented){ transition: all .2s ease; }
.u-main :deep(.ant-select-selector){ border-radius: 8px; }

/* 让 MainChat 填满剩余空间 */
.u-main :deep(.main-chat){ flex:1 1 auto; min-height:0; }
.u-main :deep(.chat-messages){ background:#fff; }
.u-main :deep(.chat-input-area){ background:#fafafa; }
</style>
