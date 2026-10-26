<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { VisualContext } from '@/api/tourExperience'
import { isKnowledgeSourceUrl } from '@/utils/tourPresentation'
const props = defineProps<{ context?: VisualContext | null; expanded?: boolean }>()
const failed = ref<string[]>([])
watch(
  () => props.context,
  () => {
    failed.value = []
  }
)
function allowedImage(value: string) {
  try {
    const url = new URL(value, location.origin)
    return (
      (url.origin === location.origin && url.pathname.startsWith('/api/v1/files/')) ||
      (url.protocol === 'https:' &&
        ['www.summerpalace.net.cn', 'r1.visitbeijing.com.cn', 'vbj-rscn.huanqiucdn.cn'].includes(
          url.hostname
        ))
    )
  } catch {
    return false
  }
}
const pictures = computed(() => props.context?.images?.filter((p) => allowedImage(p.url)) || [])
</script>
<template>
  <details
    v-if="context && (pictures.length || context.timeline?.length)"
    class="tour-visual-context"
    :open="expanded"
  >
    <summary>
      <span>{{ $t('看图与时间线') }}</span
      ><small>{{ $t(context.spot_name) }}</small>
    </summary>
    <div v-if="pictures.length" class="visual-images">
      <figure v-for="picture in pictures" :key="picture.url">
        <el-image
          v-if="!failed.includes(picture.url)"
          :src="picture.url"
          :alt="picture.label"
          :preview-src-list="pictures.map((p) => p.url)"
          :initial-index="pictures.indexOf(picture)"
          preview-teleported
          fit="cover"
          referrerpolicy="no-referrer"
          @error="failed.push(picture.url)"
        />
        <div v-else class="image-unavailable">{{ $t('图片暂时无法加载') }}</div>
        <figcaption>
          <span>{{ $t(picture.label) }}</span
          ><a
            v-if="isKnowledgeSourceUrl(picture.source)"
            :href="picture.source"
            target="_blank"
            rel="noopener noreferrer"
            >{{ $t('图片来源') }}</a
          >
        </figcaption>
      </figure>
    </div>
    <ol v-if="context.timeline?.length" class="visual-timeline">
      <li v-for="point in context.timeline" :key="String(point.year) + point.text">
        <strong>{{ point.year }}</strong
        ><span>{{ $t(point.text) }}</span>
      </li>
    </ol>
    <p>{{ $t(context.note) }}</p>
  </details>
</template>
<style scoped>
.tour-visual-context {
  margin-top: 14px;
  padding: 12px 14px;
  background: #f6f7fc;
  border: 1px solid #e9e7f5;
  border-radius: 14px;
  color: var(--text);
}
summary {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
}
summary:before {
  content: '＋';
  color: #6654c1;
}
details[open] > summary:before {
  content: '−';
}
summary small {
  font-size: 18px;
  color: var(--text-secondary);
}
.visual-images {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  overflow: auto;
}
.visual-images figure {
  margin: 0;
  flex: 1;
  min-width: 130px;
  max-width: 300px;
}
.visual-images .el-image,
.image-unavailable {
  width: 100%;
  height: 135px;
  display: block;
  border-radius: 10px;
  background: #e9eaf3;
}
.image-unavailable {
  display: grid;
  place-items: center;
  color: #768096;
  font-size: 18px;
}
figcaption {
  display: flex;
  gap: 6px;
  justify-content: space-between;
  font-size: 18px;
  line-height: 1.5;
  margin-top: 6px;
}
figcaption a {
  flex-shrink: 0;
  color: #6451b8;
}
.visual-timeline {
  padding: 0;
  list-style: none;
  margin: 14px 0 0;
  display: grid;
  gap: 10px;
}
.visual-timeline li {
  display: flex;
  gap: 14px;
  font-size: 18px;
  line-height: 1.6;
}
.visual-timeline strong {
  color: #6653ba;
  min-width: 46px;
}
.tour-visual-context > p {
  font-size: 18px;
  color: var(--text-secondary);
  margin: 10px 0 0;
  line-height: 1.5;
}
summary:focus-visible {
  outline: 2px solid #7762d5;
  outline-offset: 3px;
}
</style>
