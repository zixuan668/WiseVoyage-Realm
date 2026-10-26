<script setup lang="ts">
import { RouterView } from 'vue-router'
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { locale, t } from '@/i18n'
const route = useRoute()
const elementLocale = computed(() => locale.value === 'en' ? en : zhCn)
watch(() => [locale.value, route.meta.title], () => {
  document.title = t(route.meta.title || '景区导览') + ' | ' + t('智游知境')
}, { immediate: true })
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<style lang="scss" scoped></style>
