<!-- src/views/Agents.vue -->
<template>
  <div class="agents-page">
      
    <header class="agents-header">
      <h1 class="logo-agent">智能体</h1>
      <p class="subtitle">选择一个智能体开始对话（暂为列表展示，后续进入 /agents/:agentId）</p>
    </header>

    <section class="grid">
      <article
        v-for="agent in agents"
        :key="agent.id"
        class="card"
        @click="$router.push({ name: 'ChatHub', params: { provider: 'dify' }, query: { agent: agent.id } })"
        role="button"
        tabindex="0"
        aria-label="打开智能体对话（Dify）"
      >
        <div class="avatar">{{ agent.avatar }}</div>
        <div class="info">
          <div class="title">{{ agent.name }}</div>
          <div class="desc">{{ agent.desc }}</div>
          <div class="meta">
            <a-tag size="small" color="geekblue">Dify</a-tag>

            <!--
            <span class="host" :title="agent.dify?.baseURL || ''">{{ safeHost(agent.dify?.baseURL || '') }}</span>
              未来可能支持多个Dify实例，显示Host信息
            -->

            <a-tag v-if="agent.dify?.apiKey" size="small" color="blue">专用配置</a-tag>
            <a-tag v-else size="small" color="default">默认配置</a-tag>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { agents } from '@/agents/registry'

function safeHost(url) {
  try { return new URL(url).host } catch { return '默认' }
}
</script>

<style scoped>
.logo-agent { margin-top: 20px;}
.agents-page { padding: 20px; }
.agents-header { margin-bottom: 16px; }
.subtitle { color: #666; font-size: 14px; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.card {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  background: #F5F5F5;
  transition: box-shadow .2s ease, transform .05s ease;
}
.card:hover { box-shadow: 0 4px 18px rgba(0,0,0,.05); }
.card:active { transform: scale(.99); }

.avatar {
  width: 48px; height: 48px;
  display: grid; place-items: center;
  border-radius: 12px; background: #f5f7fa; font-size: 24px;
}

.info .title { font-weight: 600; }
.info .desc { font-size: 12px; color: #666; margin-top: 4px; line-height: 1.3; }
.info .meta { margin-top: 6px; display:flex; align-items:center; gap:6px; color:#94a3b8; font-size:12px; }
.info .host { color:#6b7280; }
</style>
