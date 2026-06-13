<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 第一板块：首帧图片上传 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🖼️ 首帧图片上传</div>
      <div class="form-section-body">
      <el-form-item label="首帧图片">
        <div class="upload-field-container">
          <UploadBox category="image" accept="image/*" @upload="handleImageUpload" @select-history="(c) => $emit('select-history', c)" />
          <FilePreview v-if="form.image_asset" :items="[form.image_asset]" @remove="form.image_asset = null" />
        </div>
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第二板块：提示词输入 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">✍️ 提示词输入</div>
      <div class="form-section-body">
      <el-form-item label="提示词">
        <el-input
          v-model="form.prompt_text"
          type="textarea"
          :rows="6"
          placeholder="描述画面如何运动、镜头、风格等（如：镜头缓慢推进，阳光洒落）"
        />
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第三板块：工作流选择 ====== -->
    <!-- <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎥 工作流选择</div>
      <div class="form-section-body">
      <el-form-item label="图生视频工作流">
        <el-select v-model="form.workflow_key" filterable allow-create placeholder="选择或手动输入 i2v_ / api 工作流" style="width:100%;">
          <el-option v-for="wf in workflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
        </el-select>
      </el-form-item>
      <el-form-item label="API 参数 JSON（可选）">
        <el-input v-model="form.api_video_params_json" type="textarea" :rows="4" placeholder='{"duration":5,"video_ratio":"9:16"}' />
      </el-form-item>
    </div>
      </div>
    </div> -->
  </el-form>
</template>

<script setup lang="ts">
import type { I2vForm, WorkflowInfo } from '../types'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'

const props = defineProps<{
  form: I2vForm
  workflows: WorkflowInfo[]
}>()

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

function handleImageUpload(file: File, category: string) {
  emit('upload', file, category, 'i2v_image')
}
</script>