/**
 * Pipelines barrel export
 * Mirrors web/pipelines/__init__.py
 */
export * from './base'
export * from './standard'
export * from './asset_based'
export * from './digital_human'
export * from './i2v'
export * from './action_transfer'

export const ALL_PIPELINES = [
  'quick_create',
  'custom_media',
  'digital_human',
  'image_to_video',
  'action_transfer',
] as const

export type PipelineKey = typeof ALL_PIPELINES[number]