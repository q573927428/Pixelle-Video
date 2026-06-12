# 终端1: 启动 FastAPI 后端
uv run python api/app.py --host 0.0.0.0 --port 8000

# 终端2: 启动 Vite 开发服务器（热加载）
cd modern_ui; pnpm run dev

# 访问: http://localhost:5173/modern/
# API 请求会自动代理到 :8000，修改代码自动热更新

uv run streamlit run web/app.py

担心海关查验会把你的心爱宝贝弄坏。真实情况是，海关比你想象的要专业，但也确实会有痕迹。


玩摄影穷到吃土？日淘二手镜头真能省出一辆车！
我干日本转运十二年，
帮好多摄影老炮转运过二手镜头，
今天给你们算笔明白账：
国内99新的，热门专业镜头，随便喊大几千上万，
日本二手平台同成色，
直接比国内便宜三分之一，甚至一半！
日本人本来就爱惜器材，
大多都是升级装备出的闲置，
成色比国内二手市场好太多，
你要是蹲到好价，淘两三个镜头，
省下的钱真的够买一辆代步小车了！
最后提个醒，找包税的靠谱转运，
这波真的血赚！


花大几万淘的中古胶片相机，就怕跨国运输震坏直接报废！
我干日本转运12年，这种娇贵货见太多了，今天给你吃颗定心丸。
其实只要做好两步，根本不用担心被震坏：
第一，找转运的时候，一定要选支持特殊加固的，
正规转运都会给胶片相机多层气泡膜裹紧，箱内塞满缓冲泡沫，还会换加厚硬箱，比卖家原包装稳多了。
第二，只要是过千的机子，一定要花几块钱买个保价，真出问题也有得赔。
所以说，只要找对转运做好这两点，放心冲你的梦中情机就完事儿！


## 待完成




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




