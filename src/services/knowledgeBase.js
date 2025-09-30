import axios from 'axios'

// 知识库服务类
class KnowledgeBaseService {
  // 初始化axios实例
  constructor() {
    //this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8080/api/v1'
    this.baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  // 获取知识库列表
  async getKnowledgeBases() {
    try {
      const response = await this.client.get('/knowledge-bases/')
      console.log('获取知识库列表成功:', response.data)
      return response.data
    } catch (error) {
      console.error('获取知识库列表失败:', error)
      throw error
    }
  }

  // 创建知识库
  async createKnowledgeBase(data) {
    try {
      const response = await this.client.post('/knowledge-bases/', data)
      console.log('创建知识库成功:', response.data)
      return response.data
    } catch (error) {
      console.error('创建知识库失败:', error)
      throw error
    }
  }

  // 获取知识库详情
  async getKnowledgeBase(id) {
    try {
      const response = await this.client.get(`/knowledge-bases/${id}`)
      return response.data
    } catch (error) {
      console.error('获取知识库详情失败:', error)
      throw error
    }
  }

  // 更新知识库
  async updateKnowledgeBase(id, data) {
    try {
      const response = await this.client.put(`/knowledge-bases/${id}`, data)
      return response.data
    } catch (error) {
      console.error('更新知识库失败:', error)
      throw error
    }
  }

  // 删除知识库
  async deleteKnowledgeBase(id) {
    try {
      const response = await this.client.delete(`/knowledge-bases/${id}`)
      return response.data
    } catch (error) {
      console.error('删除知识库失败:', error)
      throw error
    }
  }

  // 上传文件
  async uploadFile(knowledgeBaseId, file, onProgress) {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await this.client.post(
        `/knowledge-bases/${knowledgeBaseId}/files`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            if (onProgress) {
              const percent = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              )
              onProgress(percent)
            }
          }
        }
      )
      return response.data
    } catch (error) {
      console.error('文件上传失败:', error)
      throw error
    }
  }

  // 获取文件列表
  async getFiles(knowledgeBaseId) {
    try {
      const response = await this.client.get(`/knowledge-bases/${knowledgeBaseId}/files`)
      return response.data
    } catch (error) {
      console.error('获取文件列表失败:', error)
      throw error
    }
  }

  // 知识库问答（同步）
  async askQuestion(data) {
    try {
      const response = await this.client.post('/chat/ask', data)
      const out = response.data || {}
      // 统一 sources：如果后端返回了 sources_file_detail，就直接替换给 sources
      if (Array.isArray(out.sources_file_detail) && out.sources_file_detail.length) {
        out.sources = out.sources_file_detail
      }
      return out
    } catch (error) {
      console.error('问答失败:', error)
      throw error
    }
  }

  // 流式问答（SSE）
  async askQuestionStream(data, onMessage, abortController = null) {
    const resp = await fetch(`${this.baseURL}/chat/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, stream: true }),
      signal: abortController?.signal
    })

    if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: false })
    let buffer = '' // 累积文本，直到出现 \n\n 才算一个完整事件

    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

      // 一个 chunk 里可能有多条事件；循环截取
      let sepIndex
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex) // 不包含 \n\n
        buffer = buffer.slice(sepIndex + 2)

        // SSE 可能包含多行，我们只关心以 'data:' 开头的行，拼接起来
        const dataLines = rawEvent
          .split('\n')
          .map(l => l.trimStart())
          .filter(l => l && !l.startsWith(':')) // 跳过注释
          .filter(l => l.startsWith('data:'))
          .map(l => l.slice(5).trimStart()) // 去掉 'data:' 前缀

        if (dataLines.length === 0) continue

        const payloadStr = dataLines.join('\n') // 多行 data 合并（规范允许）

        try {
          const evt = JSON.parse(payloadStr)

          // 兼容三种事件：start / content / end
          // 统一 sources：如果 end 事件带了 sources_file_detail，就直接替换给 sources
          if (evt?.type === 'end' && Array.isArray(evt.sources_file_detail) && evt.sources_file_detail.length) {
            evt.sources = evt.sources_file_detail
          }

          onMessage?.(evt)
        } catch (e) {
          console.error('解析SSE数据失败:', payloadStr, e)
          // 不中断循环，继续读下一条
        }
      }
      if (done) {
      // ✅ 兜底：flush 残留片段（可能只有一行 data: ...）
      const rest = buffer.trim()
      if (rest) {
        const maybeData = rest.startsWith('data:') ? rest.slice(5).trimStart() : rest
        try {
          const evt = JSON.parse(maybeData)
          if (evt?.type === 'end' && Array.isArray(evt.sources_file_detail) && evt.sources_file_detail.length) {
            evt.sources = evt.sources_file_detail
          }
          onMessage?.(evt)
        } catch (e) {
          console.warn('flush 残留失败:', rest, e)
        }
      }
      break
    }
    }
  }

  // 获取对话列表
  async getConversations(knowledgeBaseId) {
    try {
      const response = await this.client.get(`/chat/conversations/${knowledgeBaseId}`)
      return response.data
    } catch (error) {
      console.error('获取对话列表失败:', error)
      throw error
    }
  }

  // 获取对话消息
  async getConversationMessages(conversationId) {
    try {
      const response = await this.client.get(`/chat/conversations/${conversationId}/messages`)
      return response.data
    } catch (error) {
      console.error('获取对话消息失败:', error)
      throw error
    }
  }

  // 获取文件预览URL（优先 MinIO 预签名；回退绝对地址）
  async getFilePreviewUrl(fileId) {
    const resp = await this.client.get(`/chat/files/${fileId}/open-url`)
    const { url, filename } = resp.data || {}
    // 兼容后端返回相对路径的情况：转成绝对 URL，便于 <iframe> 直开
    const absUrl = (url && url.startsWith('http'))
      ? url
      : new URL(url || '', this.baseURL).toString()
    return { url: absUrl, filename }
  }

  // 把 sources_file_detail 扩充为可点开的链接
  async enrichSourcesWithUrls(sourcesFileDetail = []) {
    const out = []
    for (const item of (sourcesFileDetail || [])) {
      try {
        if (item?.file_id == null) {
          out.push({ ...item, url: null })
          continue
        }
        const { url } = await this.getFilePreviewUrl(item.file_id)
        out.push({ ...item, url })
      } catch (e) {
        console.error('获取预览URL失败', item, e)
        out.push({ ...item, url: null })
      }
    }
    return out
  }
}

export default new KnowledgeBaseService()
