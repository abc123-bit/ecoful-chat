<template>
  <!-- UTF-8：历史消息聚合页（Dify 会话 + 知识库会话） -->
  <div class="history-page">
    <div class="section">
      <div class="section-header">
        <h2>Dify 历史会话</h2>
        <a-button type="text" @click="loadDify" :loading="loading.dify">刷新</a-button>
      </div>
      <a-list :data-source="difyList" :loading="loading.dify" :locale="{ emptyText: '暂无 Dify 会话' }">
        <template #renderItem="{ item }">
          <a-list-item class="row">
            <div class="title">{{ item.title }}</div>
            <div class="meta">{{ fmt(item.updatedAt || item.createdAt) }}</div>
            <div class="ops">
              <a-button size="small" @click="openDify(item)">打开</a-button>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <div class="section">
      <div class="section-header">
        <h2>知识库对话历史</h2>
        <div class="kb-filter">
          <a-select v-model:value="state.kbId" :options="kbOptions" placeholder="选择知识库" style="min-width:220px" @change="loadKbConvs"/>
        </div>
      </div>
      <a-list :data-source="kbConvs" :loading="loading.kb" :locale="{ emptyText: '请选择知识库' }">
        <template #renderItem="{ item }">
          <a-list-item class="row">
            <div class="title">{{ item.title }}</div>
            <div class="meta">{{ fmt(item.updatedAt || item.createdAt) }}</div>
            <div class="ops">
              <a-button size="small" @click="openRag(item)">打开</a-button>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </div>
  </div>
</template>

<script setup>
// 说明：简洁聚合页，便于从统一入口跳转到 Dify 或 RAG 对话
import { reactive, ref, onMounted } from 'vue'
import difyProvider from '@/providers/difyProvider'
import KnowledgeBaseService from '@/services/knowledgeBase'

const loading = reactive({ dify: false, kb: false })
const difyList = ref([])
const kbOptions = ref([])
const kbConvs = ref([])
const state = reactive({ kbId: null })

function fmt(t){ if(!t) return ''; return new Date(t).toLocaleString() }

async function loadDify(){
  try{ loading.dify = true; difyList.value = await difyProvider.listConversations() } finally { loading.dify = false }
}

async function initKb(){
  const list = await KnowledgeBaseService.getKnowledgeBases()
  kbOptions.value = (list||[]).map(k=>({ label:k.name, value:k.id }))
}

async function loadKbConvs(){
  if(!state.kbId){ kbConvs.value = []; return }
  try{
    loading.kb = true
    const list = await KnowledgeBaseService.getConversations(state.kbId)
    kbConvs.value = (list||[]).map(it=>({
      title: it.title || `会话 ${(it.session_id||it.id||'').slice?.(0,8)}`,
      createdAt: it.created_at,
      updatedAt: it.updated_at,
      id: it.session_id || it.id
    }))
  } finally { loading.kb = false }
}

onMounted(async ()=>{ await initKb(); await loadDify() })

// 直接打开 Dify 会话：将会话 ID 作为查询参数传递给 /chat
function openDify(item){
  const conversationId = item.providerConvId || item.id || ''
  if(!conversationId) return
  // 保持当前 agent（若你希望携带 agentId，可在此追加 query）
  // 例如：query: { conversation: conversationId, id: currentAgentId }
  
  // 直接跳转到 DifyChat，并要求它加载该会话
  // 使用 name: 'Chat'，与路由中定义一致
  
  // 带上 conversation 查询参数
  // convId 路由参数可留空（兼容定义）
  
  // eslint-disable-next-line vue/no-reserved-keys
  // @ts-ignore
  
  
  // 实际跳转
  
  
  // router 实例可通过 this.$router，这里在 <script setup> 使用全局
  window.location.assign(`/chat?conversation=${encodeURIComponent(conversationId)}`)
}

// 直接打开 RAG 会话：带上 kbId 与会话 ID，跳到 /rag-chat
function openRag(item){
  const conversationId = item.id || ''
  const kbId = state.kbId
  if(!kbId) return
  window.location.assign(`/rag-chat/${encodeURIComponent(kbId)}?conversation=${encodeURIComponent(conversationId)}`)
}
</script>

<style scoped>
.history-page{ padding: 16px; display:grid; gap:20px; max-width: 1200px; margin: 0 auto; }
.section{ background:#fff; border:1px solid #eaecef; border-radius:12px; padding: 12px; box-shadow: var(--shadow-1, 0 1px 3px rgba(0,0,0,.06)); }
.section-header{ display:flex; align-items:center; justify-content:space-between; margin-bottom: 8px; }
.section-header h2{ margin:0; font-size:16px; }
.kb-filter{ display:flex; align-items:center; gap:8px; }
.row{ display:grid; grid-template-columns: 1fr auto auto; gap:12px; }
.title{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.meta{ font-size:12px; color:#98a2b3; }

/* 响应式优化 */
@media (max-width: 992px) {
  .history-page { padding: 12px; }
  .row { grid-template-columns: 1fr auto; gap: 10px; }
  .meta { display:none; }
}

@media (max-width: 576px) {
  .section { padding: 10px; }
  .section-header h2 { font-size: 15px; }
}
</style>
