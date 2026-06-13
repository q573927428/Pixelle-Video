<template>
  <div class="upload-list">
    <div class="upload-list-header">
      <span class="upload-list-title">我的素材</span>
      <span class="upload-list-count">共 {{ uploads.length }} 个文件</span>
    </div>

    <!-- 存储空间进度条 -->
    <div v-if="storageUsage" class="storage-bar">
      <div class="storage-bar-info">
        <span>存储空间</span>
        <span v-if="!storageUsage.is_unlimited" class="storage-bar-text">
          {{ storageUsage.used_display }} / {{ storageUsage.limit_display }}
        </span>
        <span v-else class="storage-bar-text">无限制</span>
      </div>
      <el-progress
        v-if="!storageUsage.is_unlimited"
        :percentage="Math.min(storageUsage.usage_percent, 100)"
        :color="storageUsage.usage_percent > 90 ? '#f56c6c' : '#409eff'"
        :stroke-width="6"
      />
    </div>

    <div v-if="loading" style="text-align:center;padding:20px;">
      <el-icon class="is-loading" style="font-size:20px;"><svg viewBox="0 0 1024 1024"><path fill="currentColor" d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32z"/></svg></el-icon>
      <div class="small muted" style="margin-top:8px;">加载中...</div>
    </div>

    <div v-else-if="!uploads.length" class="upload-list-empty">
      <div style="font-size:32px;margin-bottom:8px;">📂</div>
      <div class="small muted">暂无上传文件</div>
    </div>

    <div v-else class="upload-list-items">
      <div v-for="item in uploads" :key="item.id" class="upload-list-item">
        <div class="upload-list-item-icon">
          <span v-if="item.category === 'audio' || item.category === 'ref_audio'">🎵</span>
          <span v-else-if="item.category === 'video'">🎬</span>
          <span v-else>🖼️</span>
        </div>
        <div class="upload-list-item-info">
          <div class="upload-list-item-name">{{ item.filename || item.name }}</div>
          <div class="upload-list-item-meta">
            <span class="small muted">{{ item.category }}</span>
            <span class="small muted" style="margin-left:8px;">{{ formatSize(item.file_size) }}</span>
          </div>
        </div>
        <div class="upload-list-item-actions">
          <el-button size="small" text @click="preview(item)">预览</el-button>
          <el-button size="small" text type="danger" @click="remove(item)">删除</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUserUploads, getUserStorageUsage, deleteUserUpload, makePreviewUrl } from '../api'

const uploads = ref<any[]>([])
const loading = ref(false)
const storageUsage = ref<any>(null)

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [uploadRes, usageRes] = await Promise.all([
      getUserUploads(),
      getUserStorageUsage(),
    ])
    uploads.value = uploadRes.records || []
    storageUsage.value = usageRes
  } catch (e: any) {
    console.warn('加载上传文件列表失败', e)
  } finally {
    loading.value = false
  }
}

function formatSize(bytes: number) {
  if (!bytes) return ''
  for (const unit of ['B', 'KB', 'MB', 'GB']) {
    if (bytes < 1024) return `${bytes.toFixed(1)}${unit}`
    bytes /= 1024
  }
  return `${bytes.toFixed(1)}TB`
}

function preview(item: any) {
  const url = makePreviewUrl(item)
  if (url) window.open(url, '_blank')
}

async function remove(item: any) {
  try {
    await ElMessageBox.confirm(`确定要删除「${item.filename || item.name}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await deleteUserUpload(item.id)
    if (res.success) {
      ElMessage.success('删除成功')
      await loadData()
    }
  } catch (_) {
    // 取消删除
  }
}
</script>

<style scoped>
.upload-list {
  padding: 12px;
}
.upload-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.upload-list-title {
  font-weight: 700;
  font-size: 14px;
}
.upload-list-count {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}
.storage-bar {
  margin-bottom: 16px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.04);
  border-radius: 10px;
}
.storage-bar-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12px;
}
.storage-bar-text {
  color: rgba(255,255,255,0.6);
}
.upload-list-empty {
  text-align: center;
  padding: 30px;
}
.upload-list-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 400px;
  overflow-y: auto;
}
.upload-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  transition: background 0.15s;
}
.upload-list-item:hover {
  background: rgba(255,255,255,0.06);
}
.upload-list-item-icon {
  font-size: 20px;
  flex-shrink: 0;
}
.upload-list-item-info {
  flex: 1;
  min-width: 0;
}
.upload-list-item-name {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-list-item-meta {
  display: flex;
  align-items: center;
}
.upload-list-item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>