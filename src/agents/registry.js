// src/agents/registry.js
// UTF-8：智能体注册表（可扩展为后端动态配置）。
// 说明：每个智能体可以单独配置 Dify 工作流的 API 地址与密钥（使用 .env 注入，避免明文）。

export const agents = [
  {
    id: 'english-daily',
    name: 'dify对话',
    desc: 'dify工作流',
    avatar: '📚', // 暂时用 emoji，当作图标占位
    dify: {
      baseURL: import.meta.env.VITE_DIFY_EN_BASE_URL1 || import.meta.env.VITE_DIFY_API_URL1,
      apiKey: import.meta.env.VITE_DIFY_EN_API_KEY1 || import.meta.env.VITE_DIFY_API_KEY1,
      appToken: import.meta.env.VITE_DIFY_EN_APP_TOKEN1 || import.meta.env.VITE_DIFY_APP_TOKEN1,
    },
  },
  {
    id: 'excel-helper',
    name: 'dify对话',
    desc: 'dify工作流',
    avatar: '📊',
    dify: {
      baseURL: import.meta.env.VITE_DIFY_EXCEL_BASE_URL2 || import.meta.env.VITE_DIFY_API_URL2,
      apiKey: import.meta.env.VITE_DIFY_EXCEL_API_KEY2 || import.meta.env.VITE_DIFY_API_KEY2,
      appToken: import.meta.env.VITE_DIFY_EXCEL_APP_TOKEN2 || import.meta.env.VITE_DIFY_APP_TOKEN2,
    },
  },
  {
    id: 'dify-official',
    name: 'dify对话',
    desc: 'dify工作流',
    avatar: '🛠️',
    dify: {
      baseURL: import.meta.env.VITE_DIFY_CODE_BASE_URL || import.meta.env.VITE_DIFY_API_URL,
      apiKey: import.meta.env.VITE_DIFY_CODE_API_KEY || import.meta.env.VITE_DIFY_API_KEY,
      appToken: import.meta.env.VITE_DIFY_CODE_APP_TOKEN || import.meta.env.VITE_DIFY_APP_TOKEN,
    },
  },
]

// 根据 ID 获取智能体配置
export function getAgentById(id) {
  return agents.find(a => a.id === id)
}
