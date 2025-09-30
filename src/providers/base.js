// UTF-8
// 说明：聊天提供者（Provider）接口定义与数据模型约定
// 本文件只定义“形状”和注释，便于适配层实现与调用层理解；无任何运行时依赖

/**
 * 统一的会话数据结构（前端标准形状）
 * @typedef {Object} ChatConversation
 * @property {string} id                本地唯一 ID（前端生成/映射）
 * @property {string} title             会话标题
 * @property {string|Date} createdAt    创建时间
 * @property {string|Date} updatedAt    更新时间
 * @property {string} provider          提供者 ID（如 'rag'、'dify'）
 * @property {string} providerConvId    提供者侧原始会话 ID（用于后续查询/删除）
 */

/**
 * 统一的消息数据结构（前端标准形状）
 * @typedef {Object} ChatMessage
 * @property {'user'|'assistant'} role  角色
 * @property {string} id                本地唯一 ID
 * @property {string} content           文本内容（已按需要渲染/原文）
 * @property {Array<any>} [files]       附件（若支持）
 * @property {Array<any>} [sources]     参考来源（RAG 可用）
 * @property {string} [messageId]       提供者消息 ID（反馈等场景需要）
 * @property {Object} [metadata]        附带元数据（token 用量等）
 * @property {string} [status]          'partial' | 'final'（流式中间/结束）
 * @property {string} [provider]        提供者 ID
 */

/**
 * Provider 能力矩阵（用于控制 UI 开关）
 * @typedef {Object} ProviderCapabilities
 * @property {boolean} streaming        是否支持流式
 * @property {{enabled:boolean, accept?:string, maxCount?:number}} files 文件上传能力
 * @property {boolean} feedback         是否支持点赞/点踩反馈
 * @property {boolean} history          是否提供会话历史
 * @property {boolean} sources          是否返回参考来源（RAG）
 * @property {boolean} editResend       是否支持消息编辑重发
 */

/**
 * Provider 接口（适配层需实现）
 * @typedef {Object} ChatProvider
 * @property {string} id                          提供者唯一 ID
 * @property {string} name                        展示名称
 * @property {ProviderCapabilities} capabilities  能力矩阵
 * @property {(context?:Object)=>Promise<ChatConversation[]>} listConversations 列出会话
 * @property {(providerConvId:string, context?:Object)=>Promise<ChatMessage[]>} getMessages 获取会话消息
 * @property {(payload:{content:string, files?:File[], providerConvId?:string, context?:Object, onEvent?:(evt:any)=>void, abortController?:AbortController})=>Promise<any>} sendMessage 发送消息（支持流式）
 * @property {(providerConvId:string)=>Promise<void>} deleteConversation 删除指定会话
 * @property {(messageId:string, rating:'like'|'dislike', reason?:string)=>Promise<void>} feedback 反馈点赞/点踩
 */

// 以上类型用于约束与说明；实际实现见各适配器文件。

