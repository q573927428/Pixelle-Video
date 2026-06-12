<template>
  <div class="upload-box-row">
    <el-upload
      class="compact-upload"
      drag
      :auto-upload="false"
      :show-file-list="false"
      :accept="accept"
      :on-change="handleChange"
    >
      <div class="compact-upload-content">
        <span class="compact-upload-icon">＋</span>
        <span>上传文件</span>
        <span class="compact-upload-hint">点击或拖拽</span>
      </div>
    </el-upload>
    <el-button size="small" class="history-btn" @click="$emit('select-history', category)">
      <span style="margin-right:4px;">📂</span> 从历史选择
    </el-button>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ category: string; accept?: string }>()
const emit = defineEmits<{
  (e: 'upload', file: File, category: string): void
  (e: 'select-history', category: string): void
}>()

function handleChange(uploadFile: any) {
  if (uploadFile.raw) {
    emit('upload', uploadFile.raw, props.category)
  }
}
</script>