/**
 * 🎥 图生视频 (Image to Video) Pipeline
 * Mirrors web/pipelines/i2v.py
 */
import type { I2vForm, WorkflowInfo } from '../types'

export interface I2vPipelineParams {
  form: I2vForm
  uploads: any[]
  workflows: WorkflowInfo[]
}

/**
 * 表单验证 - 图生视频
 */
export function validateI2vForm(form: I2vForm): string | null {
  if (!form.image_assets.length) {
    return '请上传首帧图片'
  }
  if (!form.prompt_text.trim()) {
    return '请输入提示词'
  }
  if (!form.workflow_key) {
    return '请选择图生视频工作流'
  }
  return null
}

/**
 * 构建图生视频的提交 payload
 */
export function buildI2vPayload(form: I2vForm): Record<string, any> {
  let apiVideoParams: Record<string, any> = {}
  if (form.api_video_params_json && form.api_video_params_json.trim()) {
    try {
      apiVideoParams = JSON.parse(form.api_video_params_json)
    } catch (e: any) {
      throw new Error(`JSON 参数格式错误：${e.message}`)
    }
  }

  return {
    image_assets: form.image_assets,
    prompt_text: form.prompt_text,
    workflow_key: form.workflow_key,
    api_video_params: apiVideoParams,
  }
}

/**
 * 过滤图生视频工作流列表
 * 匹配规则: api/ 开头, 或 i2v_ 前缀, 或包含 /i2v_
 */
export function filterI2vWorkflows(workflows: WorkflowInfo[]): WorkflowInfo[] {
  return workflows.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    const name = (wf.name || key).toLowerCase()
    return key.startsWith('api/') || name.startsWith('i2v_') || key.includes('/i2v_')
  })
}