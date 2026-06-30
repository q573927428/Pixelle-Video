<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="`📤 发布到 ${platformLabel}`"
    :close-on-click-modal="false"
    top="8vh"
    width="60%"
    class="publish-dialog"
    destroy-on-close
  >
    <div class="publish-layout">
      <!-- 左侧：视频预览 -->
      <div class="publish-left">
        <div class="publish-section-title">🎬 视频预览</div>
        <div class="publish-video-wrap">
          <video
            v-if="videoUrl"
            :src="videoUrl"
            controls
            muted
            playsinline
            preload="metadata"
            class="publish-video"
          />
          <div v-else class="publish-video-empty">
            <div style="font-size:32px;">🎞️</div>
            <div class="small muted">暂无视频</div>
          </div>
        </div>

        <!-- 封面设置 -->
        <div class="cover-section">
          <div class="publish-section-title">🎨 封面设置</div>
          <div class="cover-row">
            <div class="cover-item">
              <div class="cover-label">竖屏封面 (3:4)</div>
              <div class="cover-upload-wrap">
                <img v-if="frameSrc" :src="frameSrc" class="cover-preview" />
                <div v-else class="cover-placeholder">
                  <el-icon style="font-size:28px;color:#999;"><VideoCamera /></el-icon>
                  <span class="small muted">自动截取第一帧</span>
                </div>
              </div>
            </div>
            <div class="cover-item">
              <div class="cover-label">横屏封面 (4:3)</div>
              <div class="cover-upload-wrap landscape">
                <img v-if="frameSrc" :src="frameSrc" class="cover-preview" />
                <div v-else class="cover-placeholder">
                  <el-icon style="font-size:28px;color:#999;"><VideoCamera /></el-icon>
                  <span class="small muted">自动截取第一帧</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：发布配置 -->
      <div class="publish-right">
        <div class="publish-section-title">📝 发布配置</div>

        <el-form label-position="top" class="publish-form">
          <el-form-item label="视频标题">
            <div class="title-input-row">
              <el-input v-model="publishTitle" placeholder="请输入视频标题" maxlength="100" show-word-limit />
              <el-button
                type="primary"
                size="small"
                :loading="aiLoading"
                :disabled="!publishText"
                @click="handleAIGenerate"
                class="ai-btn"
              >
                <el-icon><MagicStick /></el-icon>
                {{ aiLoading ? '生成中' : 'AI生成' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item label="文案内容">
            <el-input
              v-model="publishText"
              type="textarea"
              :rows="8"
              placeholder="请输入文案内容"
              maxlength="1200"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="话题标签">
            <el-input
              v-model="publishTopics"
              placeholder="多个话题用逗号分隔，如：AI技术,数字人,短视频"
            />
          </el-form-item>

          <!-- 选择发布平台 -->
          <div class="publish-platform-select">
            <div class="publish-section-title">📤 选择发布平台</div>
            <div class="publish-platform-buttons">
              <el-button
                v-for="p in publishPlatforms"
                :key="p.key"
                :type="selectedPlatform === p.key ? p.type : 'default'"
                size="large"
                class="publish-platform-btn"
                @click="selectedPlatform = p.key"
                :plain="selectedPlatform !== p.key"
              >
                <span style="font-size:20px;margin-right:4px;">{{ p.icon }}</span>
                {{ p.label }}
              </el-button>
            </div>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="publish-footer">
        <div class="publish-status" v-if="publishStatus">
          <el-tag :type="publishSuccess ? 'success' : 'danger'" effect="dark">
            {{ publishSuccess ? '✅ 发布成功！' : '❌ 发布失败：' + publishStatus }}
          </el-tag>
        </div>
        <div class="publish-actions">
          <el-button @click="$emit('update:visible', false)" :disabled="publishing">取消</el-button>
          <el-button
            type="primary"
            @click="handlePublish"
            :loading="publishing"
            :disabled="!publishTitle || !publishText"
          >
            {{ publishing ? '发布中...' : `🚀 发布到 ${platformLabel}` }}
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, MagicStick } from '@element-plus/icons-vue'
import { generatePublishPrepare } from '../api'

const publishPlatforms = [
  { key: 'douyin', label: '抖音', icon: '🎵', type: 'danger' as const },
  { key: 'kuaishou', label: '快手', icon: '📹', type: 'primary' as const },
  { key: 'xiaohongshu', label: '小红书', icon: '📕', type: 'warning' as const },
  { key: 'shipinhao', label: '视频号', icon: '💚', type: 'success' as const },
]

const props = defineProps<{
  visible: boolean
  platform: string
  videoUrl: string
  initialTitle: string
  initialText: string
  initialTopics: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  publish: [payload: {
    platform: string
    title: string
    text: string
    topics: string
  }]
}>()

const selectedPlatform = ref('douyin')

const platformLabel = computed(() => {
  const map: Record<string, string> = {
    douyin: '抖音',
    kuaishou: '快手',
    xiaohongshu: '小红书',
    shipinhao: '视频号',
  }
  return map[selectedPlatform.value] || selectedPlatform.value
})

const publishTitle = ref('')
const publishText = ref('')
const publishTopics = ref('')

// 封面 - 自动截取视频第一帧
const frameSrc = ref<string>('')

const aiLoading = ref(false)
const publishing = ref(false)
const publishStatus = ref('')
const publishSuccess = ref(false)

watch(() => props.visible, (val) => {
  if (val) {
    // 打开时初始化数据
    selectedPlatform.value = props.platform || 'douyin'
    publishTitle.value = props.initialTitle
    publishText.value = props.initialText
    publishTopics.value = props.initialTopics
    frameSrc.value = ''
    publishing.value = false
    publishStatus.value = ''
    publishSuccess.value = false

    // 自动截取视频第一帧作为封面
    nextTick(() => captureVideoFrame())
  }
})

/** 截取视频第一帧作为封面 */
function captureVideoFrame() {
  if (!props.videoUrl) return

  const video = document.createElement('video')
  // blob URL / 本地文件不要设置 crossOrigin，否则会加载失败
  if (props.videoUrl.startsWith('http')) {
    video.crossOrigin = 'anonymous'
  }
  video.src = props.videoUrl
  video.muted = true
  video.playsInline = true
  video.preload = 'auto'
  // 微调到 0.01s 避免黑帧
  video.currentTime = 0.01

  let done = false
  function capture() {
    if (done) return
    done = true
    if (video.readyState < 2) return
    const w = video.videoWidth
    const h = video.videoHeight
    if (!w || !h) return
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, w, h)
    frameSrc.value = canvas.toDataURL('image/jpeg', 0.9)
    video.remove()
    canvas.remove()
  }

  video.oncanplay = capture
  video.onseeked = capture
}

async function handleAIGenerate() {
  const text = publishText.value?.trim()
  if (!text) {
    ElMessage.warning('没有可用的文案，无法生成标题和话题')
    return
  }
  aiLoading.value = true
  try {
    const res = await generatePublishPrepare(text)
    if (res.title) {
      publishTitle.value = res.title
    }
    if (res.topics && res.topics.length > 0) {
      publishTopics.value = res.topics.join(' ')
    }
    ElMessage.success('✅ 标题和话题已自动生成！')
  } catch (e: any) {
    ElMessage.error(`生成失败：${e?.message || '请检查LLM配置'}`)
  } finally {
    aiLoading.value = false
  }
}

async function handlePublish() {
  if (!publishTitle.value || !publishText.value) {
    ElMessage.warning('请填写标题和文案')
    return
  }
  publishing.value = true
  publishStatus.value = ''
  publishSuccess.value = false

  try {
    emit('publish', {
      platform: selectedPlatform.value,
      title: publishTitle.value,
      text: publishText.value,
      topics: publishTopics.value,
    })
    publishSuccess.value = true
    publishStatus.value = `🎉 视频已成功发布到${platformLabel.value}！`
    ElMessage.success(`发布到${platformLabel.value}成功！`)
  } catch (e: any) {
    publishStatus.value = e?.message || '发布失败，请重试'
    publishSuccess.value = false
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.publish-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  height: calc(80vh - 140px);
  min-height: 400px;
}

.publish-left,
.publish-right {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.publish-left {
  overflow-y: auto;
  overflow-x: hidden;
}

@media (max-width: 768px) {
  .publish-layout {
    grid-template-columns: 1fr;
  }
}

.publish-left,
.publish-right {
  min-width: 0;
  min-height: 0;
}

.publish-section-title {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line, rgba(255,255,255,0.1));
}

.publish-video-wrap {
  width: 100%;
  background: #000;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.publish-video {
  display: block;
  width: 100%;
  max-height: 30vh;
  object-fit: contain;
}

.publish-video-empty {
  padding: 60px 20px;
  text-align: center;
  color: var(--muted, #888);
}

.publish-platform-select {
  margin-top: 8px;
  flex-shrink: 0;
}

.publish-platform-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.publish-platform-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

/* 覆盖el-button默认样式 */
.publish-platform-btn.el-button {
  box-sizing: border-box;
  width: 100%;
  margin: 0 !important; /* 清除ElementPlus自带的margin */
  font-weight: 700;
  letter-spacing: 1px;

  /* 强制统一边框占位：不管是实心还是描边按钮，边框都占固定空间 */
  border: 2px solid transparent;
  padding-inline: 0 !important; /* 干掉el‑button默认左右内边距 */
}

.publish-form {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  min-height: 0;
}

.cover-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 12px;
}

.cover-item {
  display: grid;
  gap: 6px;
}

.cover-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text, #ccc);
}

.cover-upload-wrap {
  height: 200px;
  aspect-ratio: 3/4;
  border: 2px dashed rgba(255,255,255,0.15);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.03);
  transition: border-color 0.2s;
}
.cover-upload-wrap:hover {
  border-color: var(--el-color-primary);
}

.cover-upload-wrap.landscape {
  height: 200px;
  aspect-ratio: 4/3;
}

.cover-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.cover-section {
  margin-top: 8px;
  flex-shrink: 0;
}

.publish-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.publish-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.publish-status {
  flex: 1;
  text-align: left;
}

.title-input-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  width: 100%;
}
.title-input-row .el-input {
  flex: 1;
}
.ai-btn {
  flex-shrink: 0;
  min-width: 80px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-weight: 700;
}
</style>