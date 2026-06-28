<template>
  <div class="form-section-wrapper">
    <div class="form-section">
      <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>👤 个人名片</span>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:13px;font-weight:400;">开关</span>
          <el-switch
            :model-value="enabled"
            @update:model-value="$emit('update:enabled', $event)"
          />
        </div>
      </div>
      <div class="form-section-body" v-if="enabled">
        <el-form-item label="头衔">
          <el-input v-model="localConfig.title" placeholder="例如：创始人 & CEO" :maxlength="30" show-word-limit />
        </el-form-item>
        <el-form-item label="辅语">
          <el-input v-model="localConfig.subtitle" placeholder="例如：专注AI视频生成10年" :maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="显示时长">
          <el-radio-group v-model="localConfig.display_mode">
            <el-radio-button value="full">全视频时长</el-radio-button>
            <el-radio-button value="duration">指定秒数</el-radio-button>
          </el-radio-group>
          <div v-if="localConfig.display_mode === 'duration'" style="margin-top:8px;">
            <el-slider v-model="localConfig.duration_seconds" :min="1" :max="60" :step="1" show-input>
              <template #prepend>⏱</template>
            </el-slider>
          </div>
        </el-form-item>

        <!-- 预制名片风格 -->
        <div style="margin-bottom:14px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🎨 名片风格</span>
            <el-tag size="small" type="info" effect="plain">点击切换</el-tag>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div
              v-for="preset in presetStyles"
              :key="preset.name"
              @click="applyPreset(preset)"
              style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:6px;border:1px solid var(--el-border-color-light);cursor:pointer;transition:all 0.2s;"
              @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-color-primary)'; (e.currentTarget as HTMLElement).style.background = 'var(--el-fill-color-light)'; }"
              @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-border-color-light)'; (e.currentTarget as HTMLElement).style.background = 'transparent'; }"
            >
              <div style="flex-shrink:0;width:48px;height:28px;border-radius:4px;overflow:hidden;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <span style="font-size:9px;color:#fff;font-weight:bold;line-height:1;">👤</span>
              </div>
              <span style="font-size:12px;font-weight:500;white-space:nowrap;">{{ preset.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import type { BusinessCardConfig } from '../types'

const props = defineProps<{
  enabled: boolean
  config: BusinessCardConfig
}>()

const emit = defineEmits<{
  (e: 'update:enabled', val: boolean): void
  (e: 'update:config', val: BusinessCardConfig): void
}>()

const localConfig = reactive<BusinessCardConfig>({ ...props.config })

watch(
  () => props.config,
  (val) => {
    if (val) {
      Object.assign(localConfig, val)
    }
  },
  { deep: true }
)

watch(
  () => ({ ...localConfig }),
  (val) => {
    emit('update:config', val as BusinessCardConfig)
  },
  { deep: true }
)

interface PresetStyle {
  name: string
  config: Partial<BusinessCardConfig>
  /** 背景色（预览小图标用） */
  bgGradient: string
}

const presetStyles: PresetStyle[] = [
  {
    name: '简约白',
    config: { title: '创始人', subtitle: '诚信·专业·高效' },
    bgGradient: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
  },
  {
    name: '商务蓝',
    config: { title: 'CEO · 张总', subtitle: '专注商业创新10年' },
    bgGradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  {
    name: '科技黑',
    config: { title: '技术总监', subtitle: 'AI + 大数据驱动未来' },
    bgGradient: 'linear-gradient(135deg, #2c3e50 0%, #3498db 100%)',
  },
  {
    name: '活力橙',
    config: { title: '销售经理', subtitle: '客户至上·服务第一' },
    bgGradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  },
  {
    name: '清新绿',
    config: { title: '品牌负责人', subtitle: '绿色生活·品质之选' },
    bgGradient: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  },
  {
    name: '优雅紫',
    config: { title: '创意总监', subtitle: '设计源于生活' },
    bgGradient: 'linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%)',
  },
]

function applyPreset(preset: PresetStyle) {
  Object.assign(localConfig, {
    ...localConfig,
    ...preset.config,
  })
}
</script>