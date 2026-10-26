<script setup lang="ts">import { t } from '@/i18n'

import { computed, ref, onMounted } from 'vue'
import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'

interface SystemStatus {
  database: { status: string; error?: string }
  llm: { status: string; api_base: string; model: string; key_configured: boolean }
  tts: { status: string; engine?: string }
  asr: { status: string; engine?: string; key_configured?: boolean }
  rag: { status: string }
  digital_human: { status: string; xingyun_configured: boolean; musetalk_available: boolean }
  python_version: string
}

const loading = ref(false)
const status = ref<SystemStatus | null>(null)
const loadError = ref('')

const loadStatus = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const res = await request_handler<ResultPackage<SystemStatus>>({
      method: 'GET',
      url: '/system/status',
      headers: { Authorization: header_authorization.value },
    })
    if ((res.data as any).code === undefined) {
      // 直接返回的 dict
      status.value = res.data as any
    } else {
      const pkg = res.data as ResultPackage<SystemStatus>
      if (pkg.code === 0) status.value = pkg.data
      else loadError.value = pkg.message
    }
  } catch (e: any) {
    loadError.value = e.message || t("加载失败")
  } finally {
    loading.value = false
  }
}

const statusTag = (s: string) => (s === 'connected' || s === 'available') ? 'success' : (s === 'configured' || s === 'local_fallback') ? 'warning' : 'danger'
const statusLabel = (s: string) => {
  if (s === 'connected' || s === 'available') return t("正常")
  if (s === 'configured') return t("已配置")
  if (s === 'local_fallback') return t("本地回退")
  if (s === 'unavailable') return t("未启用")
  return t("异常")
}

const services = computed(() => {
  if (!status.value) return []
  return [
    { name: t("数据库 PostgreSQL"), status: status.value.database.status, detail: status.value.database.error ? t("异常: {p0}", {p0: status.value.database.error}) : t("连接正常") },
    { name: t("LLM 大模型"), status: status.value.llm.status, detail: `${status.value.llm.model} @ ${status.value.llm.api_base}`, extra: status.value.llm.key_configured ? t(" Key已配置") : t(" Key未配置") },
    { name: t("TTS 语音合成"), status: status.value.tts.status, detail: t(status.value.tts.engine || "未配置") },
    { name: t("ASR 语音识别"), status: status.value.asr.status, detail: t(status.value.asr.engine || "未配置") },
    { name: t("RAG 知识检索"), status: status.value.rag.status, detail: t("BM25 + TF-IDF 景区知识检索") },
    { name: t("数字人驱动"), status: status.value.digital_human.status, detail: t("星云应用：{p0}；MuseTalk：{p1}", {
      p0: t(status.value.digital_human.xingyun_configured ? "已配置" : "未配置"),
      p1: statusLabel(status.value.digital_human.musetalk_available ? 'available' : 'unavailable'),
    }) },
  ]
})

onMounted(() => { loadStatus() })
</script>

<template>
  <div class="overview-container" v-loading="loading">
    <div class="page-header">
      <h2>{{ $t("系统概览") }}</h2>
      <el-button :icon="'Refresh'" @click="loadStatus" :loading="loading">{{ $t("刷新状态") }}</el-button>
    </div>

    <el-alert v-if="loadError" :title="$t('加载失败: ') + $t(loadError)" type="error" show-icon closable style="margin-bottom:16px" />

    <!-- 服务状态卡片 -->
    <el-row :gutter="16" class="service-row">
      <el-col :span="8" v-for="svc in services" :key="svc.name" style="margin-bottom:16px">
        <el-card shadow="hover" class="service-card">
          <div class="svc-header">

            <span class="svc-name">{{ $t(svc.name) }}</span>
            <el-tag :type="statusTag(svc.status)" size="small" effect="dark">
              {{ statusLabel(svc.status) }}
            </el-tag>
          </div>
          <div class="svc-detail">{{ $t(svc.detail) }}</div>
          <div v-if="svc.extra" class="svc-extra" :class="{ warn: svc.extra.includes('未配置') }">{{ $t(svc.extra) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 环境信息 -->
    <el-card shadow="never" class="env-card" v-if="status">
      <template #header><span class="card-title">{{ $t("运行环境") }}</span></template>
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item :label='$t("Python 版本")'>{{ $t(status.python_version) }}</el-descriptions-item>
        <el-descriptions-item :label='$t("LLM 模型")'>{{ $t(status.llm.model) }}</el-descriptions-item>
        <el-descriptions-item :label='$t("API 网关")'>{{ $t(status.llm.api_base) }}</el-descriptions-item>
        <el-descriptions-item :label='$t("数据库状态")'>
          <el-tag :type="statusTag(status.database.status)" size="small">{{ $t(statusLabel(status.database.status)) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label='$t("TTS 服务")'>
          <el-tag :type="statusTag(status.tts.status)" size="small">{{ $t(statusLabel(status.tts.status)) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label='$t("ASR 服务")'>
          <el-tag :type="statusTag(status.asr.status)" size="small">{{ $t(statusLabel(status.asr.status)) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.overview-container { padding: 16px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 22px; }

.service-row { margin-bottom: 8px; }
.service-card { border-radius: 12px; height: 100%; }
.svc-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.svc-icon { font-size: 28px; }
.svc-name { font-size: 18px; font-weight: 600; flex: 1; }
.svc-detail { font-size: 18px; color: var(--text-muted); margin-bottom: 4px; }
.svc-extra { font-size: 18px; color: var(--success); &.warn { color: var(--champagne); } }

.env-card { border-radius: 12px; margin-top: 8px; }
.card-title { font-size: 18px; font-weight: 600; }
</style>
