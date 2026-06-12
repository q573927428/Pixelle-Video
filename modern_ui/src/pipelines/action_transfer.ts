/**
 * 💃 动作迁移 (Action Transfer) Pipeline
 * Mirrors web/pipelines/action_transfer.py
 */
import type { ActionForm, WorkflowInfo } from '../types'

export interface ActionTransferPipelineParams {
  form: ActionForm
  uploads: any[]
  workflows: WorkflowInfo[]
}

/**
 * 表单验证 - 动作迁移
 */
export function validateActionForm(form: ActionForm): string | null {
  if (!form.video_assets.length) {
    return '请上传参考动作视频'
  }
  if (!form.image_assets.length) {
    return '请上传目标图片'
  }
  if (!form.prompt_text.trim()) {
    return '请输入提示词'
  }
  if (!form.workflow_key) {
    return '请选择动作迁移工作流'
  }
  return null
}

/**
 * 构建动作迁移的提交 payload
 */
export function buildActionPayload(form: ActionForm): Record<string, any> {
  let apiVideoParams: Record<string, any> = {}
  if (form.api_video_params_json && form.api_video_params_json.trim()) {
    try {
      apiVideoParams = JSON.parse(form.api_video_params_json)
    } catch (e: any) {
      throw new Error(`JSON 参数格式错误：${e.message}`)
    }
  }

  return {
    video_assets: form.video_assets,
    image_assets: form.image_assets,
    prompt_text: form.prompt_text,
    duration: form.duration,
    workflow_key: form.workflow_key,
    api_video_params: apiVideoParams,
  }
}

/**
 * 过滤动作迁移工作流列表
 * 匹配规则: api/ 开头, 或 af_ 前缀, 或包含 /af_
 */
export function filterActionWorkflows(workflows: WorkflowInfo[]): WorkflowInfo[] {
  return workflows.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    const name = (wf.name || key).toLowerCase()
    return key.startsWith('api/') || name.startsWith('af_') || key.includes('/af_')
  })
}