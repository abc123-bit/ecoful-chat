<template>
  <!-- UTF-8：统一侧边栏（Provider 无关） -->
  <div class="u-sidebar">
    <div class="u-header">
      <div class="u-title">
        <span class="dot"/>
        <span class="name">{{ provider?.name || '对话' }}</span>
      </div>
      <div class="u-tools">
        <a-tooltip title="刷新历史">
          <button class="icon-btn" @click="$emit('refresh')" :disabled="loading" aria-label="刷新历史">
            <ReloadOutlined v-if="!loading"/>
            <a-spin v-else size="small"/>
          </button>
        </a-tooltip>
        <a-tooltip title="新建对话">
          <button class="icon-btn" @click="$emit('new-conversation')" aria-label="新建对话">
            <PlusOutlined/>
          </button>
        </a-tooltip>
      </div>
    </div>

    <transition-group
      v-if="conversations && conversations.length"
      name="conv-slide"
      tag="div"
      class="u-list"
    >
      <div
        v-for="c in conversations"
        :key="c.id"
        :class="['u-item', { active: c.id === currentId }]"
        @click="$emit('select', c)"
      >
        <div class="info">
          <div class="title" :title="c.title">{{ c.title }}</div>
          <div class="meta">{{ formatTime(c.updatedAt || c.createdAt) }}</div>
        </div>
        <div class="ops">
          <a-popconfirm title="确定删除该会话？" ok-text="删除" cancel-text="取消" @confirm="$emit('delete', c)">
            <DeleteOutlined class="del" aria-label="删除会话"/>
          </a-popconfirm>
        </div>
      </div>
    </transition-group>

    <div v-else class="u-empty">
      <a-empty description="暂无对话"/>
    </div>
  </div>
</template>

<script setup>
// 说明：本组件只负责展示 Provider 返回的会话列表
import { ReloadOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  provider: { type: Object, default: null },
  conversations: { type: Array, default: () => [] },
  currentId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['refresh', 'select', 'delete', 'new-conversation'])

// 简单时间格式化
function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString()
}
</script>

<style scoped>
.u-sidebar{ width:280px; background: var(--card,#fff); border-right:1px solid var(--border,#eaecef); height:100%; display:flex; flex-direction:column; }
.u-header{ display:flex; align-items:center; justify-content:space-between; padding:14px 12px; border-bottom:1px solid var(--border,#eaecef); }
.u-title{ display:flex; align-items:center; gap:8px; font-weight:600; color:var(--text-1,#1f2328); }
.dot{ width:8px; height:8px; background:var(--brand,#2563eb); border-radius:50%; display:inline-block; }
.u-tools{ display:flex; gap:8px; }
.icon-btn{ width:34px; height:34px; border-radius:10px; background:#fff; border:1px solid #e6e7eb; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; transition: all .12s; color:#4b5563; }
.icon-btn:hover{ transform: translateY(-1px); border-color:#c7d2fe; }
.u-list{ flex:1; overflow:auto; padding:8px; }
.u-item{ display:flex; align-items:center; justify-content:space-between; gap:8px; padding:10px 12px; border-radius:10px; cursor:pointer; color:#1f2328; transition: all .15s; }
.u-item:hover{ background:#f7f9fc; }
.u-item.active{ background:#eef2ff; border:1px solid #c7d2fe; }
.info{ flex:1; min-width:0; }
.title{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:14px; }
.meta{ font-size:11px; color:#8e8ea0; margin-top:2px; }
.ops .del{ color:#98a2b3; font-size:14px; }
.ops .del:hover{ color:#ff4d4f; }
.u-empty{ padding:18px; }
.conv-slide-enter-active,
.conv-slide-leave-active,
.conv-slide-move{ transition: all .2s ease; }
.conv-slide-enter-from,
.conv-slide-leave-to{ opacity:0; transform: translateY(8px); }

</style>
