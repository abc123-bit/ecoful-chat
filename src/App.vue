<template>
  <!-- UTF-8：仅渲染路由视图，侧栏与布局由 MainLayout 承载 -->
  <div id="app">
    <router-view />
  </div>
</template>

<script>
import Navigation from '@/components/Navigation.vue'
import './assets/theme.css'
export default {
  name: 'App',
  components: { Navigation }
}
</script>

<style>
#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}
</style>
