<script setup lang="ts">import { t, locale } from '@/i18n'

import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import { useResizeObserver } from '@vueuse/core'

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const props = defineProps<{
  title?: string
  data: Array<{ day: string; hour: string; count: number }>
  height?: string
}>()

function initChart() {
  if (!chartRef.value || !props.data.length) return
  chartInstance?.dispose()
  chartInstance = echarts.init(chartRef.value, 'soft-ui', { locale: locale.value === 'en' ? 'EN' : 'ZH' })

  const days = [t("周一"), t("周二"), t("周三"), t("周四"), t("周五"), t("周六"), t("周日")]
  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`)

  // 构建热力图矩阵
  const matrix: number[][] = []
  for (let dayIdx = 0; dayIdx < 7; dayIdx++) {
    const row: number[] = []
    for (let hour = 0; hour < 24; hour++) {
      const item = props.data.find(d => (d.day === ['周一','周二','周三','周四','周五','周六','周日'][dayIdx] || d.day === days[dayIdx]) && d.hour === `${String(hour).padStart(2, '0')}:00`)
      row.push(item?.count || 0)
    }
    matrix.push(row)
  }

  // 计算最大值用于颜色映射
  const maxVal = Math.max(...matrix.flat(), 1)

  const option: echarts.EChartsOption = {
    title: props.title ? {
      text: t(props.title),
      left: 'center',
      textStyle: { fontSize: 18, fontWeight: 600 },
    } : undefined,
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        return `${params.value[1]} ${params.value[0]}<br/>${t('活跃度: {p0}次', {p0: params.value[2]})}`
      },
    },
    grid: {
      left: 64, right: 18, top: props.title ? 58 : 18, bottom: 82,
    },
    xAxis: {
      type: 'category',
      data: hours,
      splitArea: { show: true },
      axisLabel: {
        fontSize: 18,
        rotate: 0,
        interval: 3, // 每3小时显示一个标签
      },
    },
    yAxis: {
      type: 'category',
      data: days,
      splitArea: { show: true },
      axisLabel: { fontSize: 18 },
    },
    visualMap: {
      min: 0,
      max: maxVal,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 8,
      inRange: {
        color: ['#eef2ff', '#e0e7ff', '#c7d2fe', '#a5b4fc', '#818cf8', '#6366f1', '#4338ca'],
      },
      textStyle: { fontSize: 18 },
    },
    series: [{
      type: 'heatmap',
      data: (() => {
        const result: [number, number, number][] = []
        for (let dayIdx = 0; dayIdx < 7; dayIdx++) {
          for (let hour = 0; hour < 24; hour++) {
            result.push([hour, dayIdx, matrix[dayIdx][hour]])
          }
        }
        return result.map(([h, d, v]) => [hours[h], days[d], v] as any)
      })(),
      label: {
        show: false,
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
    }],
  }

  chartInstance.setOption(option)
}

watch(() => props.data, () => {
  if (chartInstance) { chartInstance.dispose(); initChart() }
}, { deep: true })

useResizeObserver(chartRef, () => chartInstance?.resize())
onBeforeUnmount(() => chartInstance?.dispose())
onMounted(() => { initChart() })
watch(locale, () => initChart())
</script>

<template>
  <div ref="chartRef" :style="{ width: '100%', height: height || '420px' }" />
</template>
