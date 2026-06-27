/**
 * Pipelines barrel export
 * Mirrors web/pipelines/__init__.py
 */
export * from './base'

export * from './digital_human'

export const ALL_PIPELINES = [

  'digital_human',

] as const

export type PipelineKey = typeof ALL_PIPELINES[number]