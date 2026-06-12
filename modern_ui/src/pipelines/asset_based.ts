/**
 * 🎨 自定义素材 (Asset Based / Custom Media) Pipeline
 * Mirrors web/pipelines/asset_based.py
 */
import type { AssetForm, WorkflowInfo, BgmInfo } from '../types'

export interface AssetBasedPipelineParams {
  form: AssetForm
  uploads: any[]
  workflows: WorkflowInfo[]
  bgmFiles: BgmInfo[]
}

/**
 * 表单验证 - 自定义素材
 */
export function validateAssetForm(form: AssetForm): string | null {
  if (!form.assets.length) {
    return '请上传素材图片或视频'
  }
  return null
}

/**
 * 构建自定义素材的提交 payload
 */
export function buildAssetPayload(form: AssetForm): Record<string, any> {
  return Object.fromEntries(
    Object.entries({
      assets: form.assets,
      video_title: form.video_title,
      intent: form.intent,
      duration: form.duration,
      source: form.source,
      analysis_image_workflow: form.analysis_image_workflow,
      analysis_video_workflow: form.analysis_video_workflow,
      analysis_vlm_model: form.analysis_vlm_model,
      api_video_workflow: form.api_video_workflow,
      api_video_params: form.api_video_params,
      voice_id: form.voice_id,
      tts_speed: form.tts_speed,
      bgm_path: form.bgm_path,
      bgm_volume: form.bgm_volume,
      bgm_mode: form.bgm_mode,
    }).filter(([_, v]) => v !== '' && v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0))
  )
}