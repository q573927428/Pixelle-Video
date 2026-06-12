/**
 * 🤖 数字人口播 (Digital Human) Pipeline
 * Mirrors web/pipelines/digital_human.py
 */
import type { DigitalForm, WorkflowInfo } from '../types'

export interface DigitalHumanPipelineParams {
  form: DigitalForm
  uploads: any[]
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
}

export interface DigitalHumanValidation {
  valid: boolean
  message: string
}

/**
 * 表单验证 - 数字人口播
 */
export function validateDigitalForm(form: DigitalForm): DigitalHumanValidation {
  if (!form.character_asset) {
    return { valid: false, message: '请上传角色图片' }
  }
  if (form.mode === 'digital') {
    if (!form.goods_asset) {
      return { valid: false, message: '请上传商品图片' }
    }
    if (!form.goods_text && !form.goods_title) {
      return { valid: false, message: '请填写口播文案或商品标题' }
    }
  }
  if (form.mode === 'customize' && !form.goods_text) {
    return { valid: false, message: '请填写自定义口播文案' }
  }
  return { valid: true, message: '' }
}

/**
 * 构建数字人口播的 TTS 参数
 */
export function buildDigitalTtsParams(form: DigitalForm, text: string, outputPath: string): Record<string, any> {
  const ttsParams: Record<string, any> = {
    text,
    output_path: outputPath,
    inference_mode: form.tts_inference_mode,
  }

  if (form.tts_inference_mode === 'local') {
    ttsParams.voice = form.tts_voice
    ttsParams.speed = form.tts_speed
  } else if (form.tts_inference_mode === 'voxcpm_api') {
    ttsParams.cfg = form.voxcpm_cfg || 2.0
    ttsParams.normalize = form.voxcpm_normalize || false
    ttsParams.denoise = form.voxcpm_denoise || false
    if (form.voxcpm_control_instruction) {
      ttsParams.control_instruction = form.voxcpm_control_instruction
    }
    if (form.voxcpm_use_prompt_text) {
      ttsParams.use_prompt_text = true
      if (form.voxcpm_prompt_text) {
        ttsParams.prompt_text = form.voxcpm_prompt_text
      }
    }
    if (form.ref_audio) {
      ttsParams.ref_audio = form.ref_audio
    }
  } else if (form.tts_inference_mode === 'comfyui') {
    if (form.tts_workflow) {
      ttsParams.workflow = form.tts_workflow
    }
    if (form.ref_audio) {
      ttsParams.ref_audio = form.ref_audio
    }
  }

  return ttsParams
}

/**
 * 构建数字人口播的提交 payload
 */
export function buildDigitalPayload(form: DigitalForm): Record<string, any> {
  return Object.fromEntries(
    Object.entries({
      mode: form.mode,
      character_asset: form.character_asset,
      goods_asset: form.goods_asset,
      goods_title: form.goods_title,
      goods_text: form.goods_text,
      workflow_config: form.workflow_config,
      tts_inference_mode: form.tts_inference_mode,
      tts_engine: form.tts_engine,
      tts_voice: form.tts_voice,
      tts_speed: form.tts_speed,
      tts_workflow: form.tts_workflow,
      ref_audio: form.ref_audio,
      voxcpm_cfg: form.voxcpm_cfg,
      voxcpm_normalize: form.voxcpm_normalize,
      voxcpm_denoise: form.voxcpm_denoise,
      voxcpm_control_instruction: form.voxcpm_control_instruction,
      voxcpm_use_prompt_text: form.voxcpm_use_prompt_text,
      voxcpm_prompt_text: form.voxcpm_prompt_text,
    }).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
  )
}