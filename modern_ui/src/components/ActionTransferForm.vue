<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 第一板块：参考动作视频上传 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎬 参考动作视频上传</div>
      <div class="form-section-body">
      <el-form-item label="参考动作视频">
        <div class="upload-field-container">
          <UploadBox category="video" accept="video/*" @upload="handleVideoUpload" @select-history="(c) => $emit('select-history', c)" />
          <FilePreview v-if="form.video_asset" :items="[form.video_asset]" @remove="form.video_asset = null" />
        </div>
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第二板块：目标人物/图片上传 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🧑 目标人物/图片上传</div>
      <div class="form-section-body">
      <el-form-item label="目标人物/图片">
        <div class="upload-field-container">
          <UploadBox category="image" accept="image/*" @upload="handleImageUpload" @select-history="(c) => $emit('select-history', c)" />
          <FilePreview v-if="form.image_asset" :items="[form.image_asset]" @remove="form.image_asset = null" />
        </div>
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第三板块：提示词与参数配置 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">⚙️ 提示词与参数配置</div>
      <div class="form-section-body">
      <el-form-item label="提示词">
        <el-input
          v-model="form.prompt_text"
          type="textarea"
          :rows="5"
          placeholder="描述迁移后的画面风格..."
        />
      </el-form-item>
      <el-form-item label="时长（秒）">
        <el-slider v-model="form.duration" :min="1" :max="30" show-input />
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第四板块：工作流选择 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🔄 工作流选择</div>
      <div class="form-section-body">
      <el-form-item label="动作迁移工作流">
        <el-select v-model="form.workflow_key" filterable allow-create placeholder="选择或手动输入 af_ / api 工作流" style="width:100%;">
          <el-option v-for="wf in workflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
        </el-select>
      </el-form-item>
      <el-form-item label="API 参数 JSON（可选）">
        <el-input v-model="form.api_video_params_json" type="textarea" :rows="4" placeholder='{"duration":5}' />
      </el-form-item>
    </div>
      </div>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import type { ActionForm, WorkflowInfo } from '../types'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'

defineProps<{
  form: ActionForm
  workflows: WorkflowInfo[]
}>()

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

function handleVideoUpload(file: File, category: string) {
  emit('upload', file, category, 'action_video')
}

function handleImageUpload(file: File, category: string) {
  emit('upload', file, category, 'action_image')
}
</script>