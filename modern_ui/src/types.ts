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



export interface RemoteComfyConfig {
  enabled: boolean
  base_url: string
  image_workflow_id: string
  video_workflow_id: string
  customize_workflow_id: string
  tts_workflow_id: string
}

export interface DigitalWorkflowConfig {
  first_workflow_path: string
  second_workflow_path: string
  third_workflow_path: string
  api_image_workflow: string
  api_video_workflow: string
  api_video_params: Record<string, any>
}

export interface VideoApiParams {
  duration: number
  resolution: string
  aspect_ratio: string
  negative_prompt: string
  watermark: boolean
}

// ===== 文字叠加配置基础字段（字幕和标题共用，前后端完全一致） =====
export interface TextOverlayBase {
  enabled: boolean
  font_size: number
  font_color: string
  font_family: string
  font_weight: number
  position_x: number
  position_y: number
  max_width: number
  letter_spacing: number
  font_border_width: number
  font_border_color: string
  background_color: string
  /** 背景透明度 0.0-1.0（前后端统一使用浮点） */
  background_opacity: number
  background_padding: string
  background_radius: number
}

// ===== 字幕配置接口（继承文字叠加基础，无额外字段） =====
export interface SubtitleConfig extends TextOverlayBase {
}

// ===== 标题配置接口（继承文字叠加基础 + 标题特有字段） =====
export type DisplayMode = 'full' | 'duration'

export type TitleTextAlign = 'left' | 'center' | 'right'

export interface TitleOverlayConfig extends TextOverlayBase {
  /** 标题文字内容（支持多行，用 \n 分隔） */
  text: string
  /** 文字对齐方式 */
  text_align: TitleTextAlign
  /** 显示模式：full=全视频时长, duration=指定秒数 */
  display_mode: DisplayMode
  /** 当 display_mode='duration' 时显示秒数 */
  duration_seconds: number
}

// ===== 个人名片配置接口 =====
export interface BusinessCardConfig {
  enabled: boolean
  title: string
  subtitle: string
  display_mode: DisplayMode
  duration_seconds: number
}

// ===== 背景音乐配置接口 =====
export interface BgmConfig {
  enabled: boolean
  selected_bgm: string | null
  volume: number
  custom_bgm: string | null
}

// ===== 画中画混剪配置接口 =====
export interface PipMixConfig {
  enabled: boolean
  overlay_video: string | null
  overlay_image: string | null
  position_x: number
  position_y: number
  width: number
  height: number
  opacity: number
}

export interface DigitalForm {
  mode: 'customize'
  ai_title: string
  ai_topics: string
  character_asset: string | null
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
  // 第三板块：服务配置 - 前置图片生成
  image_service_mode: 'runninghub' | 'api'
  image_api_model: string
  // 第三板块：服务配置 - 口播视频合成
  video_service_mode: 'runninghub' | 'api'
  video_api_model: string
  video_api_params: VideoApiParams
  // ===== 字幕配置 =====
  subtitle_enabled: boolean
  subtitle_config: SubtitleConfig
  // ===== 网感剪辑相关配置 =====
  internet_clip_enabled: boolean
  title_overlay_config: TitleOverlayConfig
  business_card_config: BusinessCardConfig
  bgm_config: BgmConfig
  pip_mix_config: PipMixConfig
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