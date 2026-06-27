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
  { key: 'digital_human', icon: '🤖', name: '数字人', badge: 'Digital', desc: '角色图 + 商品图 + 口播合成' },
]

export const PIPELINE_NAMES: Record<string, string> = {
  digital_human: '数字人',
}
