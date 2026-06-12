/**
 * ⚡ 快速创作 (Quick Create / Standard) Pipeline
 * Mirrors web/pipelines/standard.py
 */
import type { QuickForm, WorkflowInfo, TemplateInfo, BgmInfo } from '../types'

export interface StandardPipelineParams {
  form: QuickForm
  templates: TemplateInfo[]
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
  bgmFiles: BgmInfo[]
}

/**
 * 表单验证 - 快速创作
 */
export function validateStandardForm(form: QuickForm): string | null {
  if (!form.text.trim()) {
    return '请输入主题或文案'
  }
  if (!form.frame_template) {
    return '请选择画面模板'
  }
  return null
}

/**
 * 构建快速创作的提交 payload
 */
export function buildStandardPayload(form: QuickForm): Record<string, any> {
  const payload: Record<string, any> = {
    text: form.text,
    mode: form.mode,
    title: form.title,
    frame_template: form.frame_template,
    tts_inference_mode: form.tts_inference_mode,
    media_workflow: form.media_workflow,
    video_fps: form.video_fps,
    prompt_prefix: form.prompt_prefix,
    bgm_path: form.bgm_path,
    bgm_volume: form.bgm_volume,
  }

  if (form.mode === 'generate') {
    payload.n_scenes = form.n_scenes
    payload.min_narration_words = form.min_narration_words
    payload.max_narration_words = form.max_narration_words
    payload.min_image_prompt_words = form.min_image_prompt_words
    payload.max_image_prompt_words = form.max_image_prompt_words
  }

  if (form.tts_inference_mode === 'local') {
    payload.tts_speed = form.tts_speed
    payload.tts_voice = form.tts_voice
  } else if (form.tts_inference_mode === 'voxcpm_api') {
    payload.voxcpm_cfg = form.voxcpm_cfg
    payload.voxcpm_normalize = form.voxcpm_normalize
    payload.voxcpm_denoise = form.voxcpm_denoise
    payload.voxcpm_control_instruction = form.voxcpm_control_instruction
    payload.voxcpm_use_prompt_text = form.voxcpm_use_prompt_text
    payload.voxcpm_prompt_text = form.voxcpm_prompt_text
    if (form.ref_audio) payload.ref_audio = form.ref_audio
  } else if (form.tts_inference_mode === 'comfyui') {
    payload.tts_workflow = form.tts_workflow
    if (form.ref_audio) payload.ref_audio = form.ref_audio
  }

  return Object.fromEntries(
    Object.entries(payload).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
  )
}