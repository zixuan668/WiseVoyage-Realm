<script setup lang="ts">
import type { ScenicGalleryPhoto } from '@/data/scenicDetail'

defineProps<{
  spot: { name: string; nameEn?: string }
  photos: ScenicGalleryPhoto[]
}>()

defineEmits<{ close: []; viewer: [open: boolean] }>()
</script>

<template>
  <div class="gallery-panel" role="dialog" aria-modal="true" :aria-label="spot.name + ' 图库'">
    <div class="gallery-card">
      <div class="photo-grid">
        <div v-for="photo in photos" :key="photo.id" class="photo">
          <img :src="photo.src" :alt="photo.caption" loading="lazy" decoding="async" />
          <span>{{ photo.caption }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.gallery-panel {
  position: absolute;
  inset: 0;
  z-index: 30;
  background: #fff;
  overflow: hidden;
  animation: gallery-in 0.32s cubic-bezier(0.22, 0.68, 0.28, 1) both;
}

.gallery-card {
  position: absolute;
  inset: var(--content-top, 52px) 0 0;
  overflow-y: auto;
  padding: 8px 8px calc(env(safe-area-inset-bottom, 0px) + 96px);
  background: #fff;
  scrollbar-width: none;
}

.gallery-card::-webkit-scrollbar { width: 0; height: 0; display: none; }

.photo-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.photo {
  position: relative;
  overflow: hidden;
  aspect-ratio: 1 / 1;
  border-radius: 18px;
  background: #f1f1f1;
}

.photo img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo span {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 10px 8px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.62));
  color: #fff;
  font-size: 18px;
  font-weight: 500;
  line-height: 1.2;
}

@keyframes gallery-in {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .gallery-panel { animation: none; }
}
</style>
