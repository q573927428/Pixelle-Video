# 批量生成实现总结

## 1. 后端 API

### 新增 schema: `api/schemas/video.py`
- `VideoBatchGenerateRequest`: 批量请求体，包含 `topics`（主题列表）、`title_prefix`（标题前缀）、以及所有共享配置字段（TTS、画面模板、BGM 等）

### 新增 endpoint: `api/routers/video.py` → `POST /api/video/generate/batch`
- 创建一个父级批量任务，返回 `task_id` + `total_videos`
- 后台按顺序生成每个主题的视频
- 使用 `task_manager.update_progress()` 报告整体进度
- 遇到单个视频失败不会影响其他视频（继续下一项）
- 任务完成时 result 包含 `results[]`, `errors[]`, `success_count`, `failed_count`

## 2. 前端 UI (Vue 3 + Element Plus)

### `modern_ui/src/types.ts` → `QuickForm` 新增字段
```ts
batch_mode: boolean
batch_topics: string
batch_title_prefix: string
```

### `modern_ui/src/views/QuickCreateView.vue`
- `generate()` 根据 `batch_mode` 自动选择批量/单视频逻辑
- `generateBatch()`: 解析 `batch_topics`（按换行分割），构建 payload，调用 `POST /api/video/generate/batch`
- `pollBatchTask()`: 独立的轮询器（`batchPollTimer`），监控批量任务进度
- 完成时显示：成功/失败计数，第一个成功视频预览

### `modern_ui/src/components/QuickCreateForm.vue`
- 第一板块顶部新增「批量生成模式」开关（Checkbox）
- 批量模式下显示：
  - 批量信息提示
  - 多行 textarea 输入主题（每行一个）
  - 标题前缀输入
  - 分镜数量滑块
- 非批量模式保持原有 UI 不变