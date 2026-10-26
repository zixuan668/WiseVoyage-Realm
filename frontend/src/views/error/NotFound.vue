<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <main class="not-found">
    <section>
      <span class="status-code">404</span>
      <h1>{{ $t("页面不存在") }}</h1>
      <p>{{ $t("请检查地址，或返回首页。") }}</p>
      <el-button type="primary" @click="router.push('/home')">{{ $t("返回首页") }}</el-button>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.not-found { display: grid; place-items: center; min-height: 100vh; padding: 24px; background: var(--canvas); }
section { width: min(100%, 440px); padding: 48px 32px; text-align: center; border-radius: 24px; background: var(--surface); box-shadow: var(--shadow-panel); }
.status-code { font-size: 56px; color: var(--brand-600); }
h1 { margin: 16px 0; font-size: 24px; color: var(--ink-900); }
p { margin: 0 0 28px; line-height: 1.8; color: var(--ink-500); }
</style>
