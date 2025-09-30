# Dify API 配置指南

## 问题原因
出现 `HTTP error! status: 404` 错误通常是因为以下原因之一：

1. **未配置API密钥** - 最常见的原因
2. **API URL不正确** - 使用了错误的端点
3. **应用类型不匹配** - 使用了Agent应用而不是对话应用
4. **API密钥无效或过期**

## 解决步骤

### 1. 获取Dify API密钥
1. 访问 [Dify控制台](https://dify.ai)
2. 登录你的账户
3. 创建一个**对话应用**（不是Agent应用）
4. 在应用设置中找到"API访问"
5. 复制API密钥

### 2. 配置环境变量
编辑项目根目录的 `.env` 文件：

```env
# Dify API 配置
VITE_DIFY_API_URL=https://api.dify.ai/v1
VITE_DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxxxxxxxx
```

**重要说明：**
- `VITE_DIFY_API_KEY` 通常以 `app-` 开头
- 如果使用自部署的Dify，修改 `VITE_DIFY_API_URL` 为你的服务器地址

### 3. 重启开发服务器
配置完成后，必须重启开发服务器：

```bash
# 停止当前服务器 (Ctrl+C)
# 然后重新启动
npm run dev
```

### 4. 验证配置
重启后，打开浏览器控制台（F12），你应该看到类似的日志：

```
Dify Service初始化:
Base URL: https://api.dify.ai/v1
API Key存在: true
```

## 常见问题排查

### 404错误的具体原因：

1. **API密钥未配置**
   - 错误信息：`未配置 VITE_DIFY_API_KEY`
   - 解决：在.env文件中设置正确的API密钥

2. **API端点不存在**
   - 错误信息：`API端点不存在 (404)`
   - 可能原因：
     - 使用了Agent应用而不是对话应用
     - API URL配置错误
     - Dify服务不可用

3. **权限问题**
   - 401错误：API密钥无效
   - 403错误：权限不足

### 调试步骤：

1. **检查网络连接**
   ```bash
   curl -I https://api.dify.ai/v1/chat-messages
   ```

2. **验证API密钥**
   - 确保API密钥没有多余的空格
   - 确保使用的是对话应用的API密钥

3. **查看控制台日志**
   - 打开浏览器开发者工具
   - 查看Console和Network标签页的错误信息

## 测试API连接
你可以使用curl命令测试API是否可用：

```bash
curl -X POST 'https://api.dify.ai/v1/chat-messages' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "inputs": {},
    "query": "hello",
    "response_mode": "blocking",
    "user": "test"
  }'
```

## 替代方案
如果Dify API不可用，你可以：

1. **使用模拟数据测试界面**
2. **连接其他兼容的API**
3. **使用本地部署的Dify**

## 需要帮助？
如果问题仍然存在，请提供：
1. 浏览器控制台的完整错误信息
2. .env文件的配置（隐藏API密钥）
3. 使用的Dify应用类型（对话应用/Agent应用）