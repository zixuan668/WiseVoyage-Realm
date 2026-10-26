<script lang="ts" setup>
import BrandLogo from '@/components/BrandLogo.vue'
import { computed, ref, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import type { MenuInstance } from 'element-plus'
import { locale } from '@/i18n'
import { isCollapse } from '@/utils/navbar'
import { adminDestinations, adminGroups, activeAdminDestination } from '@/utils/adminNavigation'

const route = useRoute()
const menu = ref<MenuInstance>()
const viewport = ref<HTMLElement>()
const active = computed(() => activeAdminDestination(route.path))
const selectedPath = computed(() => active.value?.path || '')
const initialGroups = active.value?.group ? [active.value.group] : []
const marker = ref({ transform: 'translate3d(0,0,0)', width: '0px', height: '0px', opacity: 0 })
const markerReady = ref(false)
let observer: ResizeObserver | undefined
let frame = 0
let disposed = false

function syncMarker() {
  const root = viewport.value
  if (!root || disposed) return
  const items = root.querySelectorAll<HTMLElement>('[data-admin-path]')
  let target = Array.from(items).find(item => item.dataset.adminPath === selectedPath.value)
  if (!target || !target.getClientRects().length) {
    target = Array.from(root.querySelectorAll<HTMLElement>('[data-admin-group]'))
      .find(item => item.dataset.adminGroup === active.value?.group)?.querySelector<HTMLElement>('.el-sub-menu__title') || undefined
  }
  if (!target || !target.getClientRects().length) { marker.value.opacity = 0; return }
  const box = target.getBoundingClientRect(), parent = root.getBoundingClientRect()
  marker.value = { transform: `translate3d(${box.left - parent.left}px,${box.top - parent.top}px,0)`, width: `${box.width}px`, height: `${box.height}px`, opacity: 1 }
  if (!markerReady.value) requestAnimationFrame(() => { if (!disposed) markerReady.value = true })
}

function scheduleMarker() {
  if (disposed) return
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(syncMarker)
}

async function revealActiveGroup() {
  await nextTick()
  if (!isCollapse.value && active.value?.group) menu.value?.open(active.value.group)
  scheduleMarker()
}

watch(() => route.path, revealActiveGroup)
watch(isCollapse, revealActiveGroup)
watch(locale, async () => { await nextTick(); scheduleMarker() })
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(scheduleMarker)
    if (viewport.value) observer.observe(viewport.value)
  }
  window.addEventListener('resize', scheduleMarker)
  document.fonts?.ready.then(scheduleMarker)
  revealActiveGroup()
})
onBeforeUnmount(() => { disposed = true; observer?.disconnect(); cancelAnimationFrame(frame); window.removeEventListener('resize', scheduleMarker) })
</script>

<template>
  <div class="aside-shell admin-navigation" :class="{ collapsed: isCollapse }">
    <div class="brand-block"><BrandLogo :compact="isCollapse" :icon-only="isCollapse" /></div>
    <div ref="viewport" class="menu-viewport" @transitionend="scheduleMarker">
      <div class="menu-active-indicator" :class="{ ready: markerReady }" :style="marker" aria-hidden="true"></div>
      <el-menu ref="menu" router :default-active="selectedPath" :default-openeds="initialGroups"
        :collapse="isCollapse" :collapse-transition="false" unique-opened class="enterprise-menu"
        @open="scheduleMarker" @close="scheduleMarker">
        <el-menu-item v-for="item in adminDestinations.filter(item => !item.group)" :key="item.path" :index="item.path" :data-admin-path="item.path" :aria-current="selectedPath === item.path ? 'page' : undefined">
          <el-icon><component :is="item.icon" /></el-icon><span>{{ $t(item.label) }}</span>
        </el-menu-item>
        <template v-for="group in adminGroups" :key="group.key">
          <div v-if="group.caption" v-show="!isCollapse" class="menu-caption" role="presentation">{{ $t(group.caption) }}</div>
          <el-sub-menu :index="group.key" :data-admin-group="group.key">
            <template #title><el-icon><component :is="group.icon" /></el-icon><span>{{ $t(group.label) }}</span></template>
            <el-menu-item v-for="item in adminDestinations.filter(item => item.group === group.key)" :key="item.path" :index="item.path" :data-admin-path="item.path" :aria-current="selectedPath === item.path ? 'page' : undefined"><span>{{ $t(item.label) }}</span></el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.aside-shell { min-height:100vh;box-sizing:border-box;padding:18px 12px 16px;color:var(--text);background:var(--glass); }
.brand-block { display:flex;align-items:center;min-height:54px;padding:0 10px 18px;border-bottom:1px solid var(--glass-line); }
.menu-viewport { position:relative;isolation:isolate; }
.menu-active-indicator { position:absolute;top:0;left:0;z-index:0;pointer-events:none;border-radius:12px;background:var(--glass-raised,#eef2ff); }
.menu-active-indicator.ready { transition:transform 200ms cubic-bezier(.2,0,0,1),width 200ms ease-out,height 200ms ease-out,opacity 150ms ease-out; }
.menu-caption { padding:20px 12px 8px;color:var(--text-secondary);font-size:18px;font-weight:700;letter-spacing:.04em; }
.enterprise-menu { position:relative;z-index:1;--el-menu-bg-color:transparent;--el-menu-text-color:var(--text-secondary);--el-menu-hover-bg-color:transparent;--el-menu-active-color:var(--champagne-text);border-right:0;background:transparent; }
.admin-navigation .enterprise-menu :deep(.el-menu-item),.admin-navigation .enterprise-menu :deep(.el-sub-menu__title) { min-height:52px;margin:3px 0;border-radius:12px;font-size:18px;font-weight:600;transition:color 150ms ease-out,background-color 150ms ease-out; }
.admin-navigation .enterprise-menu :deep(.el-menu-item.is-active) { color:var(--champagne-text);background:transparent!important;box-shadow:none!important; }
.admin-navigation .enterprise-menu :deep(.el-menu--inline) { background:transparent!important; }
.admin-navigation .enterprise-menu :deep(.el-menu-item:hover),.admin-navigation .enterprise-menu :deep(.el-sub-menu__title:hover) { background:rgba(99,102,241,.045); }
.enterprise-menu :deep(.el-icon) { color:inherit;font-size:18px; }
.enterprise-menu.el-menu--collapse { width:48px; }
.enterprise-menu :deep(.el-sub-menu__title:focus-visible),.enterprise-menu :deep(.el-menu-item:focus-visible) { outline:2px solid var(--champagne-text);outline-offset:-3px; }
.collapsed .brand-block { justify-content:center;padding-left:0;padding-right:0; }
@media(prefers-reduced-motion:reduce) { .menu-active-indicator.ready { transition:none; } }
</style>
