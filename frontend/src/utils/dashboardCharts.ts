import type { EChartsOption } from 'echarts'
import type { ComprehensiveData } from '@/api/analytics'
import { t } from '@/i18n'

const text = '#56647b'
const axisLabel = { color: text, fontSize: 18, margin: 12, hideOverlap: true }

/** Reserve separate bands for the legend, axis titles and horizontal dates. */
export function serviceTrendOption(trend: ComprehensiveData['daily_trend'], width: number): EChartsOption {
  return {
    color: ['#5145cd', '#8591ed', '#169b80'],
    tooltip: { trigger: 'axis', confine: true, textStyle: { fontSize: 18 } },
    legend: {
      type: 'scroll', top: 0, left: 'center', itemWidth: 22, itemHeight: 12, itemGap: 22,
      textStyle: { fontSize: 18, color: text },
      data: [t('服务人次'), t('提问数'), t('满意度(%)')],
    },
    grid: { left: 8, right: 12, top: 78, bottom: 16, containLabel: true },
    xAxis: {
      type: 'category', boundaryGap: false, data: trend.map(d => d.date),
      axisLabel: {
        ...axisLabel, rotate: 0, showMinLabel: true, showMaxLabel: true,
        interval: Math.max(0, Math.ceil(trend.length / (width < 560 ? 5 : 7)) - 1),
        formatter: (date: string) => date.length > 5 ? date.slice(-5) : date,
      },
      axisTick: { show: false },
    },
    yAxis: [
      { type: 'value', name: t('数量'), minInterval: 1, nameGap: 20,
        nameTextStyle: { fontSize: 18, color: text }, axisLabel,
        splitLine: { lineStyle: { color: '#e9edf5', type: 'dashed' } } },
      { type: 'value', name: '%', min: 0, max: 100, interval: 25, nameGap: 20,
        nameTextStyle: { fontSize: 18, color: text }, axisLabel, splitLine: { show: false } },
    ],
    series: [
      { name: t('服务人次'), type: 'line', data: trend.map(d => d.sessions), symbol: 'none',
        lineStyle: { width: 3 }, areaStyle: { opacity: .06 } },
      { name: t('提问数'), type: 'line', data: trend.map(d => d.questions), symbol: 'none',
        lineStyle: { width: 3 }, areaStyle: { opacity: .08 } },
      { name: t('满意度(%)'), type: 'line', yAxisIndex: 1, data: trend.map(d => d.satisfaction),
        lineStyle: { width: 2.5, type: 'dashed' }, symbol: 'none' },
    ],
  }
}

export function popularSpotsOption(ranking: ComprehensiveData['spot_ranking'], width: number): EChartsOption {
  const spots = ranking.slice(0, 10)
  const labelWidth = Math.min(180, Math.max(90, Math.round(width * .3)))
  return {
    tooltip: { trigger: 'axis', confine: true, axisPointer: { type: 'shadow' }, textStyle: { fontSize: 18 } },
    grid: { left: labelWidth + 12, right: 46, top: 18, bottom: 68 },
    xAxis: { type: 'value', minInterval: 1, name: t('会话数'), nameLocation: 'middle', nameGap: 30,
      axisLabel, nameTextStyle: { fontSize: 18, color: text },
      splitLine: { lineStyle: { color: '#e9edf5', type: 'dashed' } } },
    yAxis: { type: 'category', inverse: true, data: spots.map(s => t(s.spot_name)),
      axisLabel: { ...axisLabel, fontSize: 18, width: labelWidth, overflow: 'truncate', interval: 0 },
      axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: 'bar', data: spots.map(s => s.session_count), barMaxWidth: 24,
      itemStyle: { color: '#7775e7', borderRadius: [0, 7, 7, 0] },
      label: { show: true, position: 'right', distance: 8, fontSize: 18, color: '#475569' } }],
  }
}
