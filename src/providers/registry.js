// UTF-8
// 说明：Provider 注册表与查找工具，统一管理可用的聊天提供者

import ragProvider from './ragProvider'
import difyProvider from './difyProvider'

// 已注册的提供者列表（顺序可用于 UI 默认顺序）
export const providers = [
  ragProvider,
  difyProvider,
]

// 根据 ID 查找提供者
export function getProviderById(id) {
  return providers.find(p => p.id === id)
}

