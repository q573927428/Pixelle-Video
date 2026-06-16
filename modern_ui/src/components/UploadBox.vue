<template>
  <div class="upload-box-row">
    <el-upload
      class="compact-upload"
      drag
      multiple
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

<style scoped>
.upload-box-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.compact-upload {
  flex: 1;
  min-width: 0;
}
.compact-upload :deep(.el-upload-dragger) {
  width: 100%;
  border-radius: 10px;
  border: 1px dashed rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.02);
  transition: border-color 0.2s, background 0.2s;
}
.compact-upload :deep(.el-upload-dragger:hover) {
  border-color: rgba(99, 102, 241, 0.5);
  background: rgba(99, 102, 241, 0.04);
}
.compact-upload-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  white-space: nowrap;
}
.compact-upload-icon {
  font-size: 18px;
  font-weight: 700;
  color: rgba(255,255,255,0.4);
}
.compact-upload-hint {
  font-size: 12px;
  color: rgba(255,255,255,0.3);
}
.history-btn {
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── 移动端适配 ── */
@media (max-width: 640px) {
  .upload-box-row {
    flex-direction: column;
  }
  .compact-upload-content {
    justify-content: center;
    font-size: 14px;
  }
  .history-btn {
    width: 100%;
  }
}
</style>