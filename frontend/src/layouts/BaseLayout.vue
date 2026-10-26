<script lang="ts" setup>
import { isCollapse } from '@/utils/navbar'
import AslideComponent from '@/components/AslideComponent.vue'
import NavbarComponent from '@/components/NavbarComponent.vue'
import { RouterView } from 'vue-router'
import { onMounted, onBeforeUnmount } from 'vue'

const narrowScreen = window.matchMedia('(max-width: 1100px)')
const syncSidebar = () => { isCollapse.value = narrowScreen.matches }
onMounted(() => {
  syncSidebar()
  narrowScreen.addEventListener('change', syncSidebar)
})
onBeforeUnmount(() => narrowScreen.removeEventListener('change', syncSidebar))
</script>

<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '72px' : '248px'" class="layout-aside">
      <el-scrollbar>
        <AslideComponent />
      </el-scrollbar>
    </el-aside>

    <el-container class="header-and-content-container">
      <NavbarComponent />
      <el-main>
        <el-scrollbar>
          <div class="content-stage">
            <router-view v-slot="{ Component }">
              <transition name="slide-fade" mode="out-in">
                <component :is="Component" />
              </transition>
            </router-view>
          </div>
        </el-scrollbar>
      </el-main>
    </el-container>
  </el-container>
</template>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
  background: var(--canvas);
}

.layout-aside {
  position: relative;
  z-index: 4;
  overflow: hidden;
  background: var(--brand-950);
  border-right: 1px solid var(--glass-line);
  box-shadow: var(--glass-shadow);
  transition: width 0.24s ease;
}

.header-and-content-container {
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
}

.el-main {
  min-height: 0;
  padding: 0;
  background: var(--canvas);
}
</style>
