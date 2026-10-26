<script setup lang="ts">
import { locale, setLocale, t } from '@/i18n'
withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
</script>
<template>
  <div class="app-language" role="group" :aria-label="t('界面语言')">
    <button type="button" lang="zh-CN" :aria-pressed="locale === 'zh'" :disabled="disabled" @click="setLocale('zh')">中文</button>
    <button type="button" lang="en" :aria-pressed="locale === 'en'" :disabled="disabled" @click="setLocale('en')">English</button>
  </div>
</template>
<style scoped>
.app-language{display:inline-flex;gap:3px;padding:4px;border-radius:14px;background:var(--surface-subtle,#f2f5f9);flex:none}
button{border:0;background:transparent;color:var(--text-secondary,#58677e);font:inherit;font-size:18px;padding:7px 10px;border-radius:10px;cursor:pointer;white-space:nowrap;transition:background .18s,color .18s}
button[aria-pressed="true"]{background:#eeedff;color:var(--text-secondary,#58677e)}
button:focus-visible{outline:2px solid #5042eb;outline-offset:2px}
button:disabled{opacity:.5;cursor:wait}
</style>