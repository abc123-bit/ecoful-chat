// src/router/index.js
// UTF-8：恢复为侧栏导航 + 内容区的布局结构（使用 MainLayout 承载）
import { createRouter, createWebHistory } from 'vue-router'
const MainLayout = () => import('@/layouts/MainLayout.vue')
const KnowledgeBase = () => import('@/views/KnowledgeBase.vue')
const Agents = () => import('@/views/Agents.vue')
const History = () => import('@/views/History.vue')
const ChatHub = () => import('@/views/UnifiedChat.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [{
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/agents' },
      { path: 'agents', name: 'Agents', component: Agents, meta: { title: '智能体 - EcofulChat' } },
      { path: 'knowledge-base', name: 'KnowledgeBase', component: KnowledgeBase, meta: { title: '知识库管理 - EcofulChat' } },
      { path: 'history', name: 'History', component: History, meta: { title: '历史消息 - EcofulChat' } },
      { path: 'chat-hub/:provider?', name: 'ChatHub', component: ChatHub, meta: { title: '粤风AI - EcofulChat' } },
      {
        path: 'difyChat/:convId?',
        name: 'difyChat',
        redirect: to => ({
          name: 'ChatHub',
          params: { provider: 'dify' },
          query: { ...to.query, conversation: to.params?.convId || to.query?.conversation }
        })
      },
      {
        path: 'rag-chat/:kbId?',
        name: 'RagChat',
        redirect: to => ({
          name: 'ChatHub',
          params: { provider: 'rag' },
          query: { ...to.query, kb: to.params?.kbId || to.query?.kb }
        })
      },
    ],
  }],
  scrollBehavior: () => ({ top: 0 }),
})
router.afterEach((to) => { if (to.meta?.title) document.title = to.meta.title })
export default router
