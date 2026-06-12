<template>
  <el-dialog v-model="visible" title="从历史上传选择" width="680px" :close-on-click-modal="false">
    <div v-if="loading" style="text-align:center;padding:30px;">
      <el-icon class="is-loading" style="font-size:24px;"><svg viewBox="0 0 1024 1024"><path fill="currentColor" d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32z"/><path fill="currentColor" d="M512 736a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V768a32 32 0 0 1 32-32z"/></svg></el-icon>
      <div class="small muted" style="margin-top:12px;">加载中...</div>
    </div>
    <div v-else-if="!filteredRecords.length" style="text-align:center;padding:30px;">
      <div style="font-size:38px;margin-bottom:10px;">📂</div>
      <div class="small muted">暂无历史上传记录</div>
    </div>

    <!-- ===== 图片类：网格画廊布局 ===== -->
    <div v-else-if="layoutType === 'image'" class="history-grid">
      <div v-for="rec in filteredRecords" :key="rec.id" class="history-grid-item" @click="selectRecord(rec)">
        <div class="history-grid-preview">
          <img :src="getUrl(rec)" @error="onImgError" />
        </div>
        <div class="history-grid-info">
          <div class="history-grid-name">{{ rec.name }}</div>
        </div>
      </div>
    </div>

    <!-- ===== 视频类：卡片布局 ===== -->
    <div v-else-if="layoutType === 'video'" class="history-video-list">
      <div v-for="rec in filteredRecords" :key="rec.id" class="history-video-card" @click="selectRecord(rec)">
        <div class="history-video-preview">
          <video :src="getUrl(rec)" muted @mouseover="playHover($event)" @mouseleave="stopHover($event)" />
          <div class="history-video-play-icon">▶</div>
        </div>
        <div class="history-video-info">
          <div class="history-video-name">{{ rec.name }}</div>
          <div class="small muted">{{ rec.category }}</div>
        </div>
      </div>
    </div>

    <!-- ===== 音频类：列表布局 ===== -->
    <div v-else-if="layoutType === 'audio'" class="history-audio-list">
      <div v-for="rec in filteredRecords" :key="rec.id" class="history-audio-item" @click="selectRecord(rec)">
        <div class="history-audio-icon">🎵</div>
        <div class="history-audio-info">
          <div class="history-audio-name">{{ rec.name }}</div>
          <div class="history-audio-player">
            <audio :src="getUrl(rec)" controls @click.stop />
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 兜底：默认列表布局 ===== -->
    <div v-else class="history-default-list">
      <div v-for="rec in filteredRecords" :key="rec.id" class="history-default-item" @click="selectRecord(rec)">
        <span>📄 {{ rec.name }}</span>
        <span class="small muted">{{ rec.category }}</span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { makePreviewUrl } from '../api'

const props = defineProps<{
  modelValue: boolean
  loading: boolean
  records: any[]
  filterCategory?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'select', record: any): void
}>()

const categoryFilterMap: Record<string, string[]> = {
  image: ['image', 'character_image', 'goods_image'],
  video: ['video'],
  ref_audio: ['ref_audio'],
  character_image: ['character_image'],
  goods_image: ['goods_image'],
}

const filteredRecords = computed(() => {
  if (!props.filterCategory) return props.records
  const allowed = categoryFilterMap[props.filterCategory] || [props.filterCategory]
  return props.records.filter((r: any) => {
    const cat = (r.category || '').toLowerCase()
    return allowed.includes(cat)
  })
})

// 根据当前分类推断布局类型：图片/视频/音频各有不同的展示布局
const layoutType = computed(() => {
  const cat = props.filterCategory || ''
  if (['image', 'character_image', 'goods_image'].includes(cat)) return 'image'
  if (cat === 'video') return 'video'
  if (cat === 'ref_audio') return 'audio'
  return 'default'
})

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function selectRecord(rec: any) {
  emit('select', rec)
}

function getUrl(rec: any) {
  return makePreviewUrl(rec)
}

function isImg(name: string) {
  return /\.(jpg|jpeg|png|gif|webp)$/i.test(name)
}
function isVideo(name: string) {
  return /\.(mp4|mov|avi|mkv|webm)$/i.test(name)
}
function isAudio(name: string) {
  return /\.(mp3|wav|flac|m4a|aac|ogg)$/i.test(name)
}
function onImgError(e: Event) {
  const el = e.target as HTMLElement
  if (el?.parentElement) {
    el.parentElement.innerHTML = '<span style="font-size:28px;">🖼️</span>'
  }
}

function playHover(e: Event) {
  const video = (e.currentTarget as HTMLElement).querySelector('video')
  if (video) video.play().catch(() => {})
}
function stopHover(e: Event) {
  const video = (e.currentTarget as HTMLElement).querySelector('video')
  if (video) { video.pause(); video.currentTime = 0 }
}
</script>

<style scoped>
/* ===== 图片网格布局 ===== */
.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  max-height: 480px;
  overflow-y: auto;
  padding: 8px 4px;
}
.history-grid-item {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  background: rgba(2,6,23,0.28);
  transition: transform 0.15s, box-shadow 0.15s;
}
.history-grid-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
.history-grid-preview {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: rgba(15,23,42,0.5);
  display: grid;
  place-items: center;
}
.history-grid-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.history-grid-info {
  padding: 8px 10px;
}
.history-grid-name {
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 视频卡片布局 ===== */
.history-video-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 480px;
  overflow-y: auto;
  padding: 4px 0;
}
.history-video-card {
  display: flex;
  gap: 14px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(2,6,23,0.28);
  cursor: pointer;
  align-items: center;
  transition: background 0.15s;
}
.history-video-card:hover {
  background: rgba(30,41,59,0.5);
}
.history-video-preview {
  position: relative;
  width: 120px;
  height: 80px;
  flex-shrink: 0;
  border-radius: 10px;
  overflow: hidden;
  background: rgba(15,23,42,0.5);
  display: grid;
  place-items: center;
}
.history-video-preview video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.history-video-play-icon {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 24px;
  color: #fff;
  background: rgba(0,0,0,0.2);
  pointer-events: none;
}
.history-video-info {
  flex: 1;
  min-width: 0;
}
.history-video-name {
  font-weight: 700;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 音频列表布局 ===== */
.history-audio-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 480px;
  overflow-y: auto;
  padding: 4px 0;
}
.history-audio-item {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(2,6,23,0.28);
  cursor: pointer;
  align-items: center;
  transition: background 0.15s;
}
.history-audio-item:hover {
  background: rgba(30,41,59,0.5);
}
.history-audio-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.history-audio-info {
  flex: 1;
  min-width: 0;
}
.history-audio-name {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-audio-player audio {
  width: 100%;
  height: 36px;
}

/* ===== 默认兜底 ===== */
.history-default-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 480px;
  overflow-y: auto;
  padding: 4px 0;
}
.history-default-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(2,6,23,0.28);
  cursor: pointer;
  transition: background 0.15s;
}
.history-default-item:hover {
  background: rgba(30,41,59,0.5);
}
</style>