<!-- 暂时不用这个nav -->
<template>
  <div class="navigation">
    <div class="nav-brand">
      <h1>EcofulChat</h1>
      <span class="nav-subtitle">智能知识库助手</span>
    </div>

    <div class="nav-menu">
      <router-link to="/agents" class="nav-item" :class="{ active: $route.path.startsWith('/agents') }">
        <MessageOutlined />
        <span>智能体</span>
      </router-link>

      <router-link to="/knowledge-base" class="nav-item" :class="{ active: $route.path.startsWith('/knowledge-base') }">
        <DatabaseOutlined />
        <span>知识库</span>
      </router-link>

      <router-link to="/rag-qa" class="nav-item" :class="{ active: $route.path.startsWith('/rag-qa') || $route.path.startsWith('/rag-chat') }">
        <MessageOutlined />
        <span>知识库问答</span>
      </router-link>

      <router-link to="/history" class="nav-item" :class="{ active: $route.path.startsWith('/history') }">
        <DatabaseOutlined />
        <span>历史消息</span>
      </router-link>
    </div>

    <div class="nav-actions">
      <a-button
        type="text"
        @click="showHelp"
        :icon="h(QuestionCircleOutlined)"
      >
        帮助
      </a-button>
    </div>
  </div>
</template>

<script setup>
import { h } from 'vue'
import { message } from 'ant-design-vue'
import { MessageOutlined, DatabaseOutlined, QuestionCircleOutlined } from '@ant-design/icons-vue'

const showHelp = () => {
  message.info('使用帮助：在知识库管理页面创建知识库并上传文件，然后在智能对话页面进行问答。')
}
</script>

<style scoped>
.navigation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-brand h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

.nav-subtitle {
  font-size: 14px;
  color: #666;
}

.nav-menu {
  display: flex;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  color: #666;
  text-decoration: none;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #f0f7ff;
  color: #1890ff;
}

.nav-item.active {
  background: #e6f7ff;
  color: #1890ff;
  font-weight: 500;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

@media (max-width: 768px) {
  .navigation {
    padding: 0 16px;
  }

  .nav-brand h1 {
    font-size: 18px;
  }

  .nav-subtitle {
    display: none;
  }

  .nav-item span {
    display: none;
  }
}
</style>
