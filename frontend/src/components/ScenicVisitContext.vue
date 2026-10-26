<script setup lang="ts">
import { t, formatDate } from '@/i18n'

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Cloudy, Drizzling, Lightning, Moon, Refresh, Sunny } from '@/icons'

const props = defineProps<{
  latitude: number
  longitude: number
  spotCount?: number
  routeCount?: number
  guideCount?: number
  weatherOnly?: boolean
}>()

type Weather = {
  temperature: number
  humidity: number | null
  wind: number | null
  code: number | null
  high: number | null
  low: number | null
  rain: number | null
  time: string
  isDay: boolean
}
const weather = ref<Weather | null>(null)
const loading = ref(false)
const unavailable = ref(false)
let requestId = 0
let controller: AbortController | null = null
let refreshTimer: ReturnType<typeof setInterval> | undefined
const numberOrNull = (value: unknown) =>
  typeof value === 'number' && Number.isFinite(value) ? value : null
const display = (value: number | null) => (value === null ? '—' : Math.round(value))
const condition = computed(() => {
  const code = weather.value?.code
  if (code === null || code === undefined) return t('天气预报')
  if (code === 0) return t('晴')
  if (code <= 2) return t('晴间多云')
  if (code === 3) return t('阴')
  if (code <= 48) return t('雾')
  if (code <= 67 || (code >= 80 && code <= 82)) return t('有雨')
  if (code <= 77 || (code >= 85 && code <= 86)) return t('有雪')
  return t('雷雨')
})
const conditionIcon = computed(() => {
  const code = weather.value?.code
  if (code === null || code === undefined) return Cloudy
  if (code <= 1) return weather.value?.isDay === false ? Moon : Sunny
  if (code >= 95) return Lightning
  if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) return Drizzling
  return Cloudy
})
const dateLabel = computed(() => {
  const date = weather.value?.time.slice(0, 10)
  return date ? formatDate(date + 'T12:00:00', { month: 'short', day: 'numeric' }) : ''
})
const visitTip = computed(() => {
  if (!weather.value) return t('建议穿舒适的步行鞋，湖岸与台阶处注意脚下。')
  const { temperature, rain, wind, code } = weather.value
  if (code !== null && code >= 95) return t('有雷雨，留意景区现场提示，避免在空旷湖岸停留。')
  if (code !== null && ((code >= 71 && code <= 77) || code === 85 || code === 86))
    return t('有雪，桥面与石阶可能湿滑，注意防滑保暖。')
  if (
    (rain !== null && rain >= 50) ||
    (code !== null && ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)))
  )
    return t('带好雨具，湖岸与石阶湿滑，适当缩短露天停留。')
  if (wind !== null && wind >= 30) return t('湖边风较大，注意保暖，留意现场游船服务公告。')
  if (temperature >= 28) return t('做好防晒并及时补水，长廊沿线适合间歇休息。')
  if (temperature <= 12) return t('湖边体感偏凉，建议携带外套，安排适当休息。')
  return t('建议穿舒适的步行鞋，湖岸与台阶处注意脚下。')
})

async function refreshWeather() {
  const id = ++requestId
  controller?.abort()
  const currentController = new AbortController()
  controller = currentController
  const timeout = setTimeout(() => currentController.abort(), 12000)
  weather.value = null
  loading.value = true
  unavailable.value = false
  try {
    const params = new URLSearchParams({
      latitude: String(props.latitude),
      longitude: String(props.longitude),
      current: 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,is_day',
      daily: 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
      timezone: 'Asia/Shanghai',
      forecast_days: '1'
    })
    // Public scenic coordinates only; no user location, token or cookies are sent.
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`, {
      signal: currentController.signal,
      credentials: 'omit'
    })
    if (!response.ok) throw new Error('Weather request failed')
    const data = await response.json()
    const temperature = numberOrNull(data.current?.temperature_2m)
    const time = data.current?.time
    if (
      temperature === null ||
      typeof time !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(time)
    )
      throw new Error('Invalid weather response')
    if (id !== requestId) return
    weather.value = {
      temperature,
      time,
      isDay: data.current.is_day !== 0,
      humidity: numberOrNull(data.current.relative_humidity_2m),
      wind: numberOrNull(data.current.wind_speed_10m),
      code: numberOrNull(data.current.weather_code),
      high: numberOrNull(data.daily?.temperature_2m_max?.[0]),
      low: numberOrNull(data.daily?.temperature_2m_min?.[0]),
      rain: numberOrNull(data.daily?.precipitation_probability_max?.[0])
    }
  } catch {
    if (id === requestId) unavailable.value = true
  } finally {
    clearTimeout(timeout)
    if (id === requestId) loading.value = false
  }
}

watch(() => [props.latitude, props.longitude], refreshWeather, { immediate: true })
onMounted(() => {
  if (props.weatherOnly)
    refreshTimer = setInterval(
      () => {
        if (!document.hidden && !loading.value) void refreshWeather()
      },
      15 * 60 * 1000
    )
})
onBeforeUnmount(() => {
  requestId++
  controller?.abort()
  clearInterval(refreshTimer)
})
</script>

<template>
  <aside
    class="visit-context content-card"
    :class="{ 'visit-context--station': weatherOnly }"
    :aria-label="$t('景区天气与游览信息')"
  >
    <section class="weather-section" aria-live="polite" :aria-busy="loading">
      <header class="context-heading">
        <h3>{{ $t('今日天气') }}</h3>
        <div>
          <span>{{ $t(dateLabel) }}</span
          ><button
            type="button"
            :aria-label="$t('刷新天气')"
            :disabled="loading"
            @click="refreshWeather"
          >
            <el-icon :class="{ 'is-loading': loading }"><Refresh /></el-icon>
          </button>
        </div>
      </header>
      <template v-if="weather">
        <div class="weather-current">
          <div>
            <strong>{{ $t(Math.round(weather.temperature)) }}<small>°C</small></strong>
            <p>
              {{ $t(condition)
              }}<span>{{ $t(display(weather.low)) }}° / {{ $t(display(weather.high)) }}°</span>
            </p>
          </div>
          <span class="weather-symbol"
            ><el-icon><component :is="conditionIcon" /></el-icon
          ></span>
        </div>
        <dl class="weather-details">
          <div>
            <dt>{{ $t('降水概率') }}</dt>
            <dd>{{ $t(display(weather.rain)) }}<small>%</small></dd>
          </div>
          <div>
            <dt>{{ $t('风速') }}</dt>
            <dd>{{ $t(display(weather.wind)) }}<small>km/h</small></dd>
          </div>
          <div>
            <dt>{{ $t('湿度') }}</dt>
            <dd>{{ $t(display(weather.humidity)) }}<small>%</small></dd>
          </div>
        </dl>
        <p class="weather-source">
          <span>{{ $t(weather.time.slice(11, 16)) }} {{ $t('预报') }}</span>
        </p>
      </template>
      <div v-else class="weather-empty">
        <el-icon><Cloudy /></el-icon>
        <p>{{ $t(loading ? '正在获取景区天气' : '天气暂时不可用') }}</p>
        <button v-if="unavailable" type="button" @click="refreshWeather">
          {{ $t('重新获取') }}
        </button>
      </div>
    </section>
    <section v-if="!weatherOnly" class="context-overview">
      <h3>{{ $t('景区概况') }}</h3>
      <dl class="context-counts">
        <div>
          <dd>{{ $t(spotCount) }}</dd>
          <dt>{{ $t('景点') }}</dt>
        </div>
        <div>
          <dd>{{ $t(routeCount) }}</dd>
          <dt>{{ $t('路线') }}</dt>
        </div>
        <div>
          <dd>{{ $t(guideCount) }}</dd>
          <dt>{{ $t('数字人') }}</dt>
        </div>
      </dl>
    </section>
    <section v-if="!weatherOnly" class="context-tip">
      <h3>{{ $t('游览提示') }}</h3>
      <p>{{ $t(visitTip) }}</p>
    </section>
  </aside>
</template>

<style scoped lang="scss">
.visit-context {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 24px;
  min-width: 0;
}
h3 {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 600;
}
.context-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.context-heading > div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 18px;
}
button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  min-height: 32px;
  border: 0;
  border-radius: 10px;
  background: var(--surface-muted);
  color: var(--brand-600);
  cursor: pointer;
}
button:disabled {
  cursor: default;
  color: var(--text-muted);
}
.weather-current {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
}
.weather-current strong {
  color: var(--text);
  font-size: 42px;
  line-height: 1.1;
  font-weight: 400;
}
.weather-current strong small {
  margin-left: 5px;
  font-size: 21px;
}
.weather-current p {
  display: flex;
  gap: 12px;
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 18px;
}
.weather-current p span {
  color: var(--text-muted);
}
.weather-symbol {
  display: grid;
  place-items: center;
  width: 62px;
  height: 62px;
  border-radius: 20px;
  color: var(--brand-600);
  background: #eef2ff;
  font-size: 32px;
}
dl,
dd {
  margin: 0;
}
.weather-details {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid var(--line-soft);
}
dt {
  color: var(--text-muted);
  font-size: 18px;
}
.weather-details dd {
  margin-top: 8px;
  color: var(--text);
  font-size: 18px;
}
.weather-details small {
  margin-left: 4px;
  font-size: 18px;
  color: var(--text-muted);
}
.weather-source {
  display: flex;
  justify-content: space-between;
  margin: 0;
  color: var(--text-muted);
  font-size: 18px;
}
.weather-source a:hover {
  color: var(--brand-600);
}
.context-overview {
  padding-top: 20px;
  border-top: 1px solid var(--line-soft);
}
.context-counts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.context-counts dd {
  color: var(--brand-600);
  font-size: 23px;
  margin-bottom: 7px;
}
.context-tip {
  margin-top: auto;
  padding: 16px;
  border-radius: 16px;
  background: var(--surface-muted);
}
.context-tip h3 {
  font-size: 18px;
}
.context-tip p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 18px;
  line-height: 1.8;
}
.weather-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 178px;
  color: var(--text-muted);
}
.weather-empty .el-icon {
  font-size: 32px;
  color: var(--brand-500);
}
.weather-empty p {
  font-size: 18px;
}
.weather-empty button {
  padding: 0 12px;
}
@media (max-width: 900px) and (min-width: 601px) {
  .visit-context {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 18px 24px;
  }
  .weather-section {
    grid-row: span 2;
  }
  .context-overview {
    padding-top: 0;
    border-top: 0;
  }
  .context-tip {
    margin-top: 0;
  }
}
.visit-context--station {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 22px;
  background: #fff;
  box-shadow: none;
  .weather-section {
    display: flex;
    flex: 1;
    flex-direction: column;
    justify-content: space-between;
  }
  h3 {
    font-size: 18px;
  }
  .context-heading {
    flex-wrap: wrap;
  }
  .context-heading > div {
    font-size: 18px;
  }
  button {
    min-width: 32px;
    min-height: 32px;
    border-radius: 50%;
    background: #f8fafc;
  }
  .weather-current {
    margin: 6px 0;
  }
  .weather-current > div {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }
  .weather-current strong {
    font-size: 44px;
    font-family: var(--app-font-family);
  }
  .weather-current strong small {
    font-size: 20px;
  }
  .weather-current p {
    flex-direction: column;
    gap: 2px;
    margin: 0;
    font-size: 18px;
  }
  .weather-symbol {
    width: 44px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 22px;
  }
  .weather-symbol :deep(svg) {
    width: 30px;
    height: 30px;
  }
  .weather-details {
    grid-template-columns: 1.2fr 1fr 0.9fr;
    gap: 8px;
    padding: 8px 0;
  }
  .weather-details > div {
    display: grid;
    grid-template-rows: 1fr auto;
    min-width: 0;
  }
  .weather-details dt {
    font-size: 18px;
    overflow-wrap: anywhere;
  }
  .weather-details dd {
    margin-top: 4px;
    font-size: 18px;
    white-space: nowrap;
  }
  .weather-details small {
    font-size: 18px;
  }
  .weather-source {
    flex-wrap: wrap;
    gap: 6px 14px;
    font-size: 18px;
  }
  .weather-empty {
    min-height: 130px;
  }
  .weather-empty p {
    font-size: 18px;
  }
  .weather-empty button {
    margin-top: 14px;
    border-radius: 999px;
    padding: 4px 18px;
  }
}
</style>
