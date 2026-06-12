export interface WorkflowInfo {
  key: string
  name: string
  display_name: string
  source: string
  path: string
  workflow_id?: string
}

export interface TemplateInfo {
  key: string
  name: string
  display_name: string
  size: string
  width: number
  height: number
  orientation: string
  path: string
}

export interface BgmInfo {
  name: string
  path: string
  source: string
}

export interface UploadRecord {
  id: string
  category: string
  name: string
  path: string
  url?: string
  filename?: string
  stored_name?: string
  relative_path?: string
}

export interface HistoryDialogState {
  visible: boolean
  loading: boolean
  records: UploadRecord[]
  pendingCategory: string
}

export interface TtsVoiceInfo {
  id: string
  name: string
  locale: string
  gender: string
  engine?: string
}

export interface QuickForm {
  text: string
  mode: 'generate' | 'fixed'
  title: string
  n_scenes: number
  min_narration_words: number
  max_narration_words: number
  min_image_prompt_words: number
  max_image_prompt_words: number
  tts_inference_mode: string
  tts_engine: string
  tts_voice: string
  tts_workflow: string | null
  ref_audio: string | null
  media_workflow: string | null
  video_fps: number
  frame_template: string | null
  prompt_prefix: string
  bgm_path: string | null
  bgm_volume: number
  tts_speed: number
  voxcpm_cfg: number
  voxcpm_normalize: boolean
  voxcpm_denoise: boolean
  voxcpm_control_instruction: string
  voxcpm_use_prompt_text: boolean
  voxcpm_prompt_text: string
}

export interface AssetForm {
  assets: string[]
  image_asset: string | null
  video_asset: string | null
  video_title: string
  intent: string
  duration: number
  source: string
  analysis_image_workflow: string
  analysis_video_workflow: string
  analysis_vlm_model: string
  animation_enabled: boolean
  api_video_workflow: string
  api_video_params: Record<string, any>
  voice_id: string
  tts_speed: number
  bgm_path: string | null
  bgm_volume: number
  bgm_mode: string
}

export interface DigitalWorkflowConfig {
  first_workflow_path: string
  second_workflow_path: string
  third_workflow_path: string
  api_image_workflow: string
  api_video_workflow: string
  api_video_params: Record<string, any>
}

export interface DigitalForm {
  mode: 'digital' | 'customize'
  character_asset: string | null
  goods_asset: string | null
  goods_title: string
  goods_text: string
  workflow_config: DigitalWorkflowConfig
  tts_inference_mode: string
  tts_engine: string
  tts_voice: string
  tts_speed: number
  tts_workflow: string
  ref_audio: string
  voxcpm_cfg: number
  voxcpm_normalize: boolean
  voxcpm_denoise: boolean
  voxcpm_control_instruction: string
  voxcpm_use_prompt_text: boolean
  voxcpm_prompt_text: string
}

export interface I2vForm {
  image_asset: string | null
  prompt_text: string
  workflow_key: string
  api_video_params_json: string
}

export interface ActionForm {
  video_asset: string | null
  image_asset: string | null
  prompt_text: string
  duration: number
  workflow_key: string
  api_video_params_json: string
}

export interface ToolInfo {
  key: string
  icon: string
  name: string
  badge: string
  desc: string
}

export interface NavItem {
  key: string
  icon: string
  label: string
}

export interface WorkflowRow {
  label: string
  value: string
}