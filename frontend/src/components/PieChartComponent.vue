<script setup lang="ts">
import { t, locale } from '@/i18n'
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { useResizeObserver } from '@vueuse/core'

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const props = defineProps<{
  title?: string
  data: Array<{ name: string; value: number }>
  colors?: string[]
  height?: string
}>()

const defaultColors = ["#4f46e5", "#818cf8", "#6366f1", "#10b981", "#ec4899", "#f59e0b", "#d15d1a", "#64748b"]

function initChart() {
  if (!chartRef.value) return
  chartInstance?.dispose()
  chartInstance = echarts.init(chartRef.value, 'soft-ui', { locale: locale.value === 'en' ? 'EN' : 'ZH' })

  const option: echarts.EChartsOption = {
    title: props.title ? {
      text: t(props.title),
      left: 'center',
      textStyle: { fontSize: 18, fontWeight: 600 },
    } : undefined,
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      type: 'scroll', orient: 'horizontal',
      left: 'center', top: props.title ? 40 : 0,
      textStyle: { fontSize: 18 }, itemGap: 18,
    },
    series: [
      {
        type: 'pie',
        radius: ['35%', '60%'],
        center: ['50%', '58%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#f8fafc',
          borderWidth: 2,
        },
        label: {
          show: true, fontSize: 18, lineHeight: 22,
          alignTo: 'edge', edgeDistance: 12, overflow: 'break',
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold',
          },
        },
        data: props.data.map((item, idx) => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: props.colors?.[idx] || defaultColors[idx % defaultColors.length],
          },
        })),
      },
    ],
  }

  chartInstance.setOption(option)
}

watch(() => props.data, () => {
  if (chartInstance) {
    chartInstance.dispose()
    initChart()
  }
}, { deep: true })

useResizeObserver(chartRef, () => chartInstance?.resize())
onBeforeUnmount(() => chartInstance?.dispose())
onMounted(() => { initChart() })
watch(locale, () => initChart())
</script>

<template>
  <div ref="chartRef" :style="{ width: '100%', height: height || '380px' }" />
</template>
