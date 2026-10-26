<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Clock, Walk, Warning, ArrowDown, ArrowUp } from '@/icons'
import { locale, t } from '@/i18n'
import type { StationDirections } from '@/api/serviceStation'
import { namedWalkingPassages } from '@/utils/stationDirections'
import StationDirectionsMap from './StationDirectionsMap.vue'

const props = defineProps<{
  directions: StationDirections
  destinationName: string
  originName: string
}>()
const S = (zh: string, en: string) => (locale.value === 'en' ? en : zh)
const expanded = ref(false)
const roads = computed(() =>
  namedWalkingPassages(props.directions.sections, props.directions.destination.label)
)
const visibleRoads = computed(() => (expanded.value ? roads.value : roads.value.slice(0, 3)))
const hasSteps = computed(
  () => props.directions.has_steps || props.directions.sections.some((section) => section.steps)
)
const walkingDistance = computed(() =>
  props.directions.meters >= 1000
    ? (props.directions.meters / 1000).toFixed(2) + ' km'
    : props.directions.meters + ' m'
)
function roadName(name: string) {
  const translated = t(name)
  return locale.value === 'en' && /[\u3400-\u9fff]/.test(translated)
    ? 'Park path · ' + name
    : translated
}
watch(
  () => props.directions,
  () => {
    expanded.value = false
  }
)
</script>

<template>
  <section
    class="station-walking-directions"
    :aria-label="S('步行路线概览', 'Walking route overview')"
  >
    <header class="walking-route-heading">
      <h2>{{ S('前往', 'Walk to') }} {{ destinationName }}</h2>
      <div class="walking-route-totals">
        <span
          ><Walk aria-hidden="true" /><strong>{{ walkingDistance }}</strong></span
        >
        <span
          ><Clock aria-hidden="true" />{{ S('约', 'About') }}
          <strong>{{ directions.minutes }}</strong> {{ S('分钟', 'min') }}</span
        >
      </div>
    </header>
    <div class="walking-route-layout">
      <StationDirectionsMap :directions="directions" />
      <div class="walking-route-summary">
        <h3>{{ S('路线概览', 'Route outline') }}</h3>
        <div class="walking-route-endpoint">
          <span class="walking-point start">A</span>
          <div>
            <span>{{ S('本站出发', 'Start here') }}</span
            ><strong>{{ originName }}</strong>
          </div>
        </div>
        <ol
          id="station-walking-passages"
          class="walking-route-passages"
          :aria-label="S('主要途经路段', 'Main passages in order')"
        >
          <li v-for="(road, index) in visibleRoads" :key="index">
            <i aria-hidden="true"></i><span>{{ roadName(road) }}</span>
          </li>
          <li v-if="!roads.length">
            <i aria-hidden="true"></i><span>{{ S('沿园内步道', 'Follow the park paths') }}</span>
          </li>
        </ol>
        <button
          v-if="roads.length > 3"
          class="walking-route-expand"
          :aria-expanded="expanded"
          aria-controls="station-walking-passages"
          @click="expanded = !expanded"
        >
          {{
            expanded
              ? S('收起途经路段', 'Show fewer passages')
              : S(
                  '展开其余 ' + (roads.length - 3) + ' 段',
                  'Show ' + (roads.length - 3) + ' more passages'
                )
          }}<component :is="expanded ? ArrowUp : ArrowDown" aria-hidden="true" />
        </button>
        <div class="walking-route-endpoint">
          <span class="walking-point finish">B</span>
          <div>
            <span>{{ S('到达目的地', 'Arrive') }}</span
            ><strong>{{ destinationName }}</strong>
          </div>
        </div>
      </div>
    </div>
    <div v-if="hasSteps" class="walking-route-steps">
      <Warning aria-hidden="true" />
      <p>
        {{
          S(
            '这条路线含台阶，携带轮椅或推车请先确认现场通行条件。',
            'This route includes steps. Check access on site if using a wheelchair or stroller.'
          )
        }}
      </p>
    </div>
    <footer class="walking-route-note">
      <span>{{ S('开放与通行以现场为准。', 'Follow on-site access arrangements.') }}</span
      >
    </footer>
  </section>
</template>

<style scoped lang="scss">
.station-walking-directions {
  padding: 26px;
  border: 1px solid #e2e8f0;
  border-radius: 28px;
  background: #fff;
}
.walking-route-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}
.walking-route-heading h2 {
  font-size: 26px;
  line-height: 1.5;
  font-weight: 600;
  margin: 0;
}
.walking-route-totals {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}
.walking-route-totals > span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 20px;
}
.walking-route-totals strong {
  color: #4f46e5;
  font-size: 25px;
}
.walking-route-totals svg {
  color: #6366f1;
}
.walking-route-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(240px, 1fr);
  align-items: stretch;
  gap: 22px;
}
.walking-route-layout :deep(.station-directions-map) {
  min-width: 0;
}
.walking-route-layout :deep(.map) {
  height: 100%;
  min-height: 370px;
}
.walking-route-summary {
  padding: 22px;
  background: #f8fafc;
  border-radius: 24px;
  min-width: 0;
}
.walking-route-summary h3 {
  margin: 0 0 20px;
  font-size: 21px;
  font-weight: 600;
}
.walking-route-endpoint {
  display: flex;
  align-items: center;
  gap: 13px;
}
.walking-point {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: #fff;
  background: #6366f1;
  font: 600 18px var(--app-font-family);
  flex-shrink: 0;
}
.walking-point.finish {
  background: #4338ca;
}
.walking-route-endpoint > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.walking-route-endpoint div > span {
  color: #64748b;
  font-size: 20px;
}
.walking-route-endpoint strong {
  font-size: 21px;
  font-weight: 500;
  overflow-wrap: anywhere;
  line-height: 1.5;
}
.walking-route-passages {
  margin: 12px 0 12px 16px;
  padding: 2px 0;
  list-style: none;
  max-height: 260px;
  overflow-y: auto;
  border-left: 2px dashed #c7d2fe;
}
.walking-route-passages li {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 50px;
  padding: 8px 0 8px 18px;
  color: #4b5563;
  font-size: 20px;
  line-height: 1.5;
}
.walking-route-passages i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a5b4fc;
  flex-shrink: 0;
}
.walking-route-expand {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 50px;
  padding: 7px 0;
  color: #4f46e5;
  font-size: 20px;
  border-radius: 10px;
}
.walking-route-expand svg {
  width: 17px;
  height: 17px;
}
.walking-route-steps {
  display: flex;
  align-items: start;
  gap: 12px;
  padding: 16px 18px;
  margin-top: 20px;
  background: #fff7ed;
  border-radius: 18px;
  color: #9a3412;
}
.walking-route-steps svg {
  margin-top: 3px;
  flex-shrink: 0;
}
.walking-route-steps p {
  margin: 0;
  font-size: 20px;
  line-height: 1.8;
}
.walking-route-note {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px 20px;
  margin-top: 18px;
  color: #64748b;
  font-size: 20px;
}
@media (max-width: 1150px) {
  .walking-route-layout {
    grid-template-columns: 1fr;
  }
  .walking-route-layout :deep(.map) {
    height: 330px;
    min-height: 0;
  }
}
@media (max-width: 600px) {
  .station-walking-directions {
    padding: 20px;
  }
  .walking-route-heading h2 {
    font-size: 24px;
  }
  .walking-route-layout :deep(.map) {
    height: 280px;
  }
  .walking-route-summary {
    padding: 20px;
  }
}
</style>
