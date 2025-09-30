// UTF-8
// 说明：Dify Service 支持运行时切换配置（用于按智能体选择不同工作流）
import axios from 'axios'
import { getAgentById } from '@/agents/registry'

class DifyService {
  constructor() {
    this.baseURL = import.meta.env.VITE_DIFY_API_URL || 'https://api.dify.ai/v1'
    this.apiKey = import.meta.env.VITE_DIFY_API_KEY || ''
    this.appToken = import.meta.env.VITE_DIFY_APP_TOKEN || ''
    this.currentAgentId = null

    // 调试日志
    console.log('Dify Service初始化:')
    console.log('Base URL:', this.baseURL)
    console.log('API Key存在:', !!this.apiKey)
    console.log('App Token存在:', !!this.appToken)

    this._createClient()
  }

  // 创建 axios 客户端（内部使用）
  _createClient() {
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      }
    })
  }

  // 运行时更新配置（可用于按智能体切换工作流）
  setConfig({ baseURL, apiKey, appToken } = {}) {
    if (baseURL) this.baseURL = baseURL
    if (apiKey !== undefined) this.apiKey = apiKey
    if (appToken !== undefined) this.appToken = appToken
    this._createClient()
    console.log('[Dify] 已应用新配置:', {
      baseURL: this.baseURL,
      apiKeySet: !!this.apiKey,
      appTokenSet: !!this.appToken,
      currentAgentId: this.currentAgentId,
    })
  }

  // 按智能体 ID 应用配置（从 registry 读取 env 注入的配置）
  applyAgent(agentId) {
    this.currentAgentId = agentId || null
    const agent = agentId ? getAgentById(agentId) : null
    if (agent?.dify) {
      const { baseURL, apiKey, appToken } = agent.dify
      this.setConfig({ baseURL, apiKey, appToken })
    } else {
      // 回退到全局默认 env
      this.setConfig({
        baseURL: import.meta.env.VITE_DIFY_API_URL || this.baseURL,
        apiKey: import.meta.env.VITE_DIFY_API_KEY || this.apiKey,
        appToken: import.meta.env.VITE_DIFY_APP_TOKEN || this.appToken,
      })
    }
  }

  // 获取文件类型
  getFileType(file) {
    if (file.type.startsWith('image/')) {
      return 'image'
    } else if (file.type.startsWith('audio/')) {
      return 'audio'
    } else if (file.type.startsWith('video/')) {
      return 'video'
    } else if (file.type === 'application/pdf') {
      return 'document'
    } else if (
      file.type.includes('word') || 
      file.type.includes('excel') || 
      file.type.includes('powerpoint') ||
      file.type.includes('document') ||
      file.name.endsWith('.doc') ||
      file.name.endsWith('.docx') ||
      file.name.endsWith('.xls') ||
      file.name.endsWith('.xlsx') ||
      file.name.endsWith('.ppt') ||
      file.name.endsWith('.pptx')
    ) {
      return 'document'
    } else if (file.type.includes('text') || file.name.endsWith('.txt')) {
      return 'text'
    } else {
      return 'other'
    }
  }

  // 上传文件
  async uploadFile(file) {
    try {
      if (!this.apiKey) {
        throw new Error('演示模式下不支持文件上传，请配置API密钥以启用此功能。')
      }

      const formData = new FormData()
      formData.append('file', file)
      formData.append('user', 'user-test')

      const response = await this.client.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      console.log('文件上传成功:', response.data)
      return response.data
    } catch (error) {
      console.error('Failed to upload file:', error)
      throw error
    }
  }

  // 批量上传文件
  async uploadFiles(files) {
    try {
      if (!this.apiKey) {
        throw new Error('演示模式下不支持文件上传，请配置API密钥以启用此功能。')
      }

      const uploadPromises = files.map(file => this.uploadFile(file))
      const results = await Promise.allSettled(uploadPromises)
      
      const successfulUploads = []
      const failedUploads = []
      
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          successfulUploads.push({
            file: files[index],
            data: result.value
          })
        } else {
          failedUploads.push({
            file: files[index],
            error: result.reason
          })
        }
      })
      
      return {
        successful: successfulUploads,
        failed: failedUploads
      }
    } catch (error) {
      console.error('批量文件上传失败:', error)
      throw error
    }
  }

  // 发送消息（支持文件）
  async sendMessage(message, files = [], difyConversationId = null, onMessage = null, abortController = null) {
    try {
      // 检查必要的配置
      if (!this.apiKey) {
        // 演示模式 - 模拟AI回复
        console.warn('未配置API密钥，使用演示模式')
        return this.simulateResponse(message, files, onMessage, abortController)
      }

      // 如果有文件，先上传所有文件
      let fileReferences = []
      if (files && files.length > 0) {
        console.log('开始上传文件:', files)
        const uploadResult = await this.uploadFiles(files)
        
        if (uploadResult.successful.length > 0) {
          fileReferences = uploadResult.successful.map(item => ({
            type: this.getFileType(item.file),
            transfer_method: 'local_file',
            upload_file_id: item.data.id
          }))
          console.log('文件上传成功，文件引用:', fileReferences)
        }
        
        if (uploadResult.failed.length > 0) {
          console.warn('部分文件上传失败:', uploadResult.failed)
          // 可以选择是否继续发送消息，还是抛出错误
          // 这里我们继续发送消息，但只使用成功上传的文件
        }
      }

      const payload = {
        inputs: {},
        query: message,
        response_mode: 'streaming',
        conversation_id: difyConversationId || "",
        user: 'user-test',
        files: fileReferences
      }

      console.log('发送消息到:', `${this.baseURL}/chat-messages`)
      console.log('请求载荷:', JSON.stringify(payload, null, 2))

      const response = await fetch(`${this.baseURL}/chat-messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: abortController?.signal
      })

      console.log('响应状态:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('API错误响应:', errorText)

        if (response.status === 404) {
          const errorData = JSON.parse(errorText)
          if (errorData.message === 'Conversation Not Exists.') {
            throw new Error('对话不存在，可能已被删除。将创建新对话。')
          } else {
            throw new Error('API端点不存在 (404)。请检查:\n1. Dify API URL是否正确\n2. 使用的是对话应用而不是Agent应用\n3. API密钥是否有效')
          }
        } else if (response.status === 401) {
          throw new Error('API密钥无效 (401)。请检查VITE_DIFY_API_KEY配置')
        } else if (response.status === 403) {
          throw new Error('访问被拒绝 (403)。请检查API密钥权限')
        } else {
          throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
        }
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullResponse = ''
      let messageId = null
      let conversationIdFromResponse = difyConversationId

      try {
        while (true) {
          // 检查是否已中止
          if (abortController?.signal.aborted) {
            reader.cancel()
            throw new Error('用户停止了生成')
          }

          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                //console.log('SSE数据:', data)
                console.log('SSE数据暂时隐藏:')
                

                if (data.event === 'message') {
                  fullResponse += data.answer || ''
                  messageId = data.message_id
                  conversationIdFromResponse = data.conversation_id

                  if (onMessage) {
                    onMessage({
                      type: 'content',
                      content: fullResponse,
                      messageId,
                      conversationId: conversationIdFromResponse
                    })
                  }
                } else if (data.event === 'message_end') {
                  if (onMessage) {
                    onMessage({
                      type: 'end',
                      content: fullResponse,
                      messageId,
                      conversationId: conversationIdFromResponse,
                      metadata: data.metadata
                    })
                  }
                } else if (data.event === 'error') {
                  throw new Error(data.message || 'Stream error occurred')
                }
              } catch (e) {
                console.warn('Failed to parse SSE data:', line, e)
              }
            }
          }
        }
      } catch (error) {
        if (error.name === 'AbortError' || error.message === '用户停止了生成') {
          console.log('请求被用户中止')
          throw new Error('生成已停止')
        }
        throw error
      }

      return {
        content: fullResponse,
        messageId,
        conversationId: conversationIdFromResponse
      }
    } catch (error) {
      console.error('Dify API Error:', error)
      throw error
    }
  }

  // 演示模式 - 模拟AI回复（支持文件）
  async simulateResponse(message, files = [], onMessage, abortController = null) {
    const hasFiles = files && files.length > 0
    const fileInfo = hasFiles ? 
      `\n\n📎 已上传${files.length}个文件: ${files.map(f => f.name).join(', ')}` : 
      ''
    
    const responses = [
      `<think>用户问了一个问题${hasFiles ? '并上传了文件' : ''}，我需要友好地回应并介绍自己。</think>

你好！我是AI助手。你刚才说："${message}"${fileInfo}

我很高兴为你提供帮助！`,

      `<think>这是演示模式${hasFiles ? '，用户上传了文件' : ''}，我应该解释当前的状态，并提醒用户如何启用真实功能。</think>

这是一个演示回复。要使用真实的AI功能，请在.env文件中配置你的Dify API密钥。

目前你看到的是模拟响应，包括这段思考过程的展示。${fileInfo}`,

      `<think>用户可能想了解我的能力${hasFiles ? '并分析了上传的文件' : ''}，我应该列出一些主要功能。</think>

我可以帮你解答问题、写代码、分析文档等。目前处于演示模式。${fileInfo}

**我的主要能力包括:**
- 💬 自然语言对话
- 💻 代码编写和解释  
- 📝 文档分析和总结
- 🤔 逻辑推理和问题解决
- 🖼️ 图片和文件分析`,

      `<think>让我展示一下Markdown渲染功能${hasFiles ? '并提及上传的文件' : ''}。思考过程应该用较小字体和灰色显示。</think>

**Markdown功能测试** ${fileInfo}

1. 支持**粗体**和*斜体*
2. 支持行内代码：\`console.log('hello')\`
3. 支持链接：[Dify官网](https://dify.ai)
4. 支持图片显示（相对路径测试）：

![测试图片](/files/test/image.png)

5. 支持图片显示（绝对路径测试）：

![网络图片](https://via.placeholder.com/400x200/4A90E2/FFFFFF?text=图片显示测试)

\`\`\`javascript
// 代码块示例
function hello() {
  console.log('Hello World!');
}
\`\`\`

| 功能 | 状态 |
|------|------|
| 流式响应 | ✅ 已实现 |
| 思考过程 | ✅ 新功能 |
| Markdown | ✅ 完全支持 |
| 图片显示 | ✅ 已修复 |
| 文件上传 | ${hasFiles ? '✅ 已支持' : '❌ 未使用'} |`
    ]

    const response = responses[Math.floor(Math.random() * responses.length)]
    const messageId = 'demo_' + Date.now()

    // 模拟流式响应
    if (onMessage) {
      const words = response.split('')
      let content = ''

      for (let i = 0; i < words.length; i++) {
        // 检查是否被中止
        if (abortController?.signal.aborted) {
          console.log('演示模式：用户停止了生成')
          throw new Error('生成已停止')
        }

        content += words[i]
        onMessage({
          type: 'content',
          content,
          messageId,
          conversationId: null
        })
        // 模拟打字延迟
        await new Promise(resolve => setTimeout(resolve, 20))
      }

      onMessage({
        type: 'end',
        content,
        messageId,
        conversationId: null,
        metadata: { usage: { tokens: response.length } }
      })
    }

    return {
      content: response,
      messageId,
      conversationId: null
    }
  }

  // 获取会话列表
  async getConversations() {
    try {
      if (!this.apiKey) {
        // 演示模式：返回模拟的历史会话
        return {
          data: [
            {
              id: 'demo_conv_1',
              name: '关于JavaScript的讨论',
              created_at: new Date(Date.now() - 86400000).toISOString(), // 1天前
              inputs: {}
            },
            {
              id: 'demo_conv_2',
              name: 'Vue3开发问题',
              created_at: new Date(Date.now() - 172800000).toISOString(), // 2天前
              inputs: {}
            },
            {
              id: 'demo_conv_3',
              name: 'API集成方案',
              created_at: new Date(Date.now() - 259200000).toISOString(), // 3天前
              inputs: {}
            }
          ],
          has_more: false,
          limit: 20
        }
      }

      // 真实对话模型，发起请求
      const response = await this.client.get('/conversations', {
        params: {
          user: 'user-test',
          last_id: '',
          limit: 20
        }
      })
      return response.data
    } catch (error) {
      console.error('Failed to get conversations:', error)
      throw error
    }
  }

  // 获取会话消息
  async getConversationMessages(conversationId) {
    try {
      if (!this.apiKey) {
        // 演示模式：返回模拟的历史消息
        const demoMessages = {
          'demo_conv_1': [
            {
              id: 'msg_1',
              conversation_id: 'demo_conv_1',
              query: '什么是JavaScript闭包？',
              answer: '<think>用户问了关于JavaScript闭包的问题，我需要提供清晰的解释和示例。</think>\n\nJavaScript闭包是一个重要概念。**闭包**是指内部函数可以访问外部函数作用域中变量的特性。\n\n```javascript\nfunction outer(x) {\n  return function inner(y) {\n    return x + y; // 访问外部变量x\n  };\n}\n\nconst add5 = outer(5);\nconsole.log(add5(3)); // 输出: 8\n```',
              created_at: new Date(Date.now() - 86400000).toISOString(),
              feedback: null
            }
          ],
          'demo_conv_2': [
            {
              id: 'msg_2',
              conversation_id: 'demo_conv_2',
              query: 'Vue3的组合式API有什么优势？',
              answer: '<think>用户问Vue3组合式API的优势，我应该对比选项式API来说明。</think>\n\nVue3的**组合式API (Composition API)**有以下优势：\n\n## 主要优点\n1. **更好的逻辑复用**：通过composables实现逻辑复用\n2. **更好的TypeScript支持**：类型推断更准确\n3. **更灵活的组织**：相关逻辑可以组织在一起\n\n```vue\n<script setup>\nimport { ref, computed } from \'vue\'\n\nconst count = ref(0)\nconst doubled = computed(() => count.value * 2)\n</script>\n```',
              created_at: new Date(Date.now() - 172800000).toISOString(),
              feedback: null
            }
          ],
          'demo_conv_3': [
            {
              id: 'msg_3',
              conversation_id: 'demo_conv_3',
              query: '如何设计RESTful API？',
              answer: '<think>这是一个关于API设计的问题，我需要提供最佳实践和具体建议。</think>\n\n设计**RESTful API**的最佳实践：\n\n## 核心原则\n1. **使用HTTP动词**：GET、POST、PUT、DELETE\n2. **清晰的URL结构**：/api/v1/users/{id}\n3. **统一响应格式**：JSON格式的标准化响应\n\n## 示例设计\n```\nGET    /api/v1/users      # 获取用户列表\nPOST   /api/v1/users      # 创建新用户  \nGET    /api/v1/users/123  # 获取特定用户\nPUT    /api/v1/users/123  # 更新用户\nDELETE /api/v1/users/123  # 删除用户\n```',
              created_at: new Date(Date.now() - 259200000).toISOString(),
              feedback: null
            }
          ]
        }

        return {
          data: demoMessages[conversationId] || [],
          has_more: false,
          limit: 100
        }
      }

      const response = await this.client.get(`/messages`, {
        params: {
          conversation_id: conversationId,
          user: 'user-test',
          first_id: '',
          limit: 100
        }
      })
      return response.data
    } catch (error) {
      console.error('Failed to get conversation messages:', error)
      throw error
    }
  }

  // 反馈消息
  async feedbackMessage(messageId, rating, content = '') {
    try {
      const response = await this.client.post(`/messages/${messageId}/feedbacks`, {
        rating: rating, // 'like' or 'dislike'
        content: content,
        user: 'user-test'
      })
      return response.data
    } catch (error) {
      console.error('Failed to send feedback:', error)
      throw error
    }
  }

  // 删除会话
  async deleteConversation(conversationId) {
    try {
      // 如果是演示模式，直接返回成功
      if (!this.apiKey) {
        console.log('演示模式：模拟删除会话', conversationId)
        return { success: true }
      }

      const response = await this.client.delete(`/conversations/${conversationId}`, {
        data: {
          user: 'user-test'
        }
      })
      return response.data
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      throw error
    }
  }
}

export default new DifyService()
