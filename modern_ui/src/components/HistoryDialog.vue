<template>
  <el-dialog v-model="visible" title="从历史上传选择" width="600px" :close-on-click-modal="false">
    <div v-if="loading" style="text-align:center;padding:30px;">
      <el-icon class="is-loading" style="font-size:24px;"><svg viewBox="0 0 1024 1024"><path fill="currentColor" d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32z"/><path fill="currentColor" d="M512 736a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V768a32 32 0 0 1 32-32z"/></svg></el-icon>
      <div class="small muted" style="margin-top:12px;">加载中...</div>
    </div>
    <div v-else-if="!filteredRecords.length" style="text-align:center;padding:30px;">
      <div style="font-size:38px;margin-bottom:10px;">📂</div>
      <div class="small muted">暂无历史上传记录</div>
    </div>
    <div v-else style="display:grid;gap:10px;max-height:450px;overflow-y:auto;padding:4px 0;">
      <div v-for="rec in filteredRecords" :key="rec.id" class="history-record" style="display:flex;gap:12px;padding:10px;border:1px solid var(--line);border-radius:14px;background:rgba(2,6,23,0.28);cursor:pointer;align-items:center;" @click="selectRecord(rec)">
        <div class="history-preview" style="width:70px;height:70px;flex-shrink:0;border-radius:10px;overflow:hidden;background:rgba(15,23,42,0.5);display:grid;place-items:center;">
          <img v-if="isImg(rec.name)" :src="getUrl(rec)" style="width:100%;height:100%;object-fit:cover;" @error="onImgError" />
          <video v-else-if="isVideo(rec.name)" :src="getUrl(rec)" style="width:100%;height:100%;object-fit:cover;" muted />
          <audio v-else-if="isAudio(rec.name)" :src="getUrl(rec)" style="width:70px;height:50px;" controls />
          <span v-else style="font-size:28px;">📄</span>
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:700;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ rec.name }}</div>
          <div class="small muted" style="margin-top:2px;">{{ rec.category }}</div>
        </div>
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
</script>