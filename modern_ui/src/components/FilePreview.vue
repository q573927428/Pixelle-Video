<template>
  <div class="file-preview-wrapper">
    <div
      v-for="(item, idx) in items"
      :key="idx"
      class="file-preview-item"
      :class="{ 'is-audio': isAudio(item) }"
    >
      <div class="file-preview-inner">
        <!-- 图片预览 -->
        <img v-if="isImage(item)" class="preview-media preview-img" :src="previewUrl(item)" @click="openUrl(item)" />
        <!-- 视频预览 -->
        <video v-else-if="isVideo(item)" class="preview-media preview-video" :src="previewUrl(item)" controls @click="openUrl(item)" />
        <!-- 音频预览 -->
        <audio v-else-if="isAudio(item)" class="preview-audio" :src="previewUrl(item)" controls @click="openUrl(item)" />
        <!-- 未知文件类型 -->
        <div v-else class="preview-file"><span class="file-icon">📄</span><span class="file-name">{{ displayName(item) }}</span></div>
      </div>
      <el-button size="small" type="danger" circle class="close-btn" @click.stop="$emit('remove', idx)">
        ✕
      </el-button>
    </div>
    <div v-if="items.length === 0" class="empty-hint">暂无文件</div>
  </div>
</template>

<script setup lang="ts">
import { filePreviewUrl } from '../api'

const props = defineProps<{
  items: string[]
}>()

defineEmits<{
  (e: 'remove', index: number): void
}>()

function isImage(filePath: string): boolean {
  return /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(filePath)
}

function isVideo(filePath: string): boolean {
  return /\.(mp4|webm|avi|mov|mkv|flv)$/i.test(filePath)
}

function isAudio(filePath: string): boolean {
  return /\.(mp3|wav|ogg|aac|flac|m4a)$/i.test(filePath)
}

function previewUrl(filePath: string): string {
  return filePreviewUrl(filePath)
}

function displayName(filePath: string): string {
  return filePath.split(/[\\/]/).pop() || filePath
}

function openUrl(filePath: string) {
  const url = previewUrl(filePath)
  if (url) window.open(url, '_blank')
}
</script>

<style scoped>
.file-preview-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border: 1px dashed #e4e7ed;
  width: 100%;
  justify-content: center;
  padding: 10px;
}
.file-preview-item {
  position: relative;
  border-radius: 10px;
  flex: 0 0 auto;
  padding: 2px;
}
.file-preview-item.is-audio {
  width: 100%;
  max-width: 100%;
}
.file-preview-inner {
  border-radius: 8px;
  overflow: hidden;
}
.preview-img {
  height: 140px;
  width: auto;
  max-width: 260px;
  object-fit: contain;
  cursor: pointer;
  display: block;
  background: #f0f2f5;
}
.preview-video {
  width: 240px;
  height: 140px;
  object-fit: contain;
  background: #000;
  cursor: pointer;
  display: block;
}
.preview-audio {
  display: block;
  width: 100%;
  height: 44px;
  margin: 0;
  padding: 2px 4px;
}
.preview-file {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 16px;
  gap: 6px;
  min-width: 120px;
}
.file-icon {
  font-size: 28px;
}
.file-name {
  font-size: 12px;
  color: #606266;
  word-break: break-all;
  text-align: center;
  max-width: 120px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
}
.close-btn {
  position: absolute !important;
  top: -10px !important;
  right: -10px !important;
  width: 24px !important;
  height: 24px !important;
  padding: 0 !important;
  font-size: 11px !important;
  z-index: 10;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
.close-btn:hover {
  transform: scale(1.15);
}
.empty-hint {
  color: #c0c4cc;
  font-size: 13px;
  padding: 4px 0;
}
</style>