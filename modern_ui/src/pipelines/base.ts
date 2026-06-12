/**
 * Pipeline UI base types and interfaces
 * Mirrors web/pipelines/base.py
 */

export interface PipelineUIOption {
  key: string
  icon: string
  name: string
  badge: string
  desc: string
}

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

export interface HistoryRecord {
  id: string
  category: string
  name: string
  path: string
  url?: string
  filename?: string
  stored_name?: string
  relative_path?: string
}

export const PIPELINE_TOOLS: PipelineUIOption[] = [
  { key: 'quick_create', icon: '⚡', name: '快速创作', badge: 'Standard', desc: '文本到视频，AI 分镜/固定文案' },
  { key: 'custom_media', icon: '🎨', name: '素材创作', badge: 'Asset', desc: '上传图片/视频素材生成成片' },
  { key: 'digital_human', icon: '🤖', name: '数字人', badge: 'Digital', desc: '角色图 + 商品图 + 口播合成' },
  { key: 'image_to_video', icon: '🎥', name: '图生视频', badge: 'I2V', desc: '首帧图片驱动视频生成' },
  { key: 'action_transfer', icon: '💃', name: '动作迁移', badge: 'Action', desc: '参考视频动作迁移到目标图片' },
]

export const PIPELINE_NAMES: Record<string, string> = {
  quick_create: '快速创作',
  custom_media: '素材创作',
  digital_human: '数字人',
  image_to_video: '图生视频',
  action_transfer: '动作迁移',
}