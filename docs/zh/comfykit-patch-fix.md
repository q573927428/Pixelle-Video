# comfykit 0.1.12 补丁修复文档

> 关于生成的所有视频是runninghub工作流默认的图片和音频
> RunningHub 数字人工作流文件上传问题分析与解决方案

---

## 目录

- [1. 问题描述](#1-问题描述)
- [2. 排查过程](#2-排查过程)
- [3. 精确对比结果](#3-精确对比结果)
- [4. 代码变更详解](#4-代码变更详解)
- [5. 根因分析](#5-根因分析)
- [6. 解决方案](#6-解决方案)
- [7. 部署步骤](#7-部署步骤)
- [8. 补丁升级说明](#8-补丁升级说明)

---

## 1. 问题描述

### 现象

本地环境可以正常上传图片和音频到 RunningHub 工作流，生成视频是根据用户上传的图片和音频生成的。而服务器上面一样的代码，生成的所有视频都是 RunningHub 工作流默认的图片和音频。

### 数据流

```
用户上传图片 → temp/uploads/{user_id}/{category}/xxx.jpg
用户上传音频 → temp/uploads/{user_id}/ref_audio/xxx.mp3
        ↓
前端 buildPayload() 将本地路径发给后端
        ↓
pipelines.py _run_second_digital_workflow()
  传参: {"image": "本地路径", "audio": "本地路径", ...}
        ↓
ComfyKit.execute(workflow_id, params)
        ↓
RunningHubExecutor 需将本地文件上传到 RunningHub
        ↓
RunningHub 拿到文件后执行工作流生成视频
```

---

## 2. 排查过程

### 2.1 代码溯源

通过追踪完整代码链路：

1. **前端** `modern_ui/src/views/DigitalHumanView.vue` → `buildPayload()`
2. **API 路由** `api/routers/pipelines.py` → `_run_second_digital_workflow()`
3. **服务层** `pixelle_video/service.py` → `execute_with_concurrency()`
4. **ComfyKit** `.venv/Lib/site-packages/comfykit/` 包

### 2.2 关键定位点

在 `api/routers/pipelines.py` 第 259-314 行的 `_run_second_digital_workflow()` 函数中，本地文件路径被直接传给 ComfyKit：

```python
workflow_params = {
    "videoimage": generated_image,    # 本地路径
    "image": generated_image,
    "input_image": generated_image,
    ...
    "audio": audio_path,              # 本地路径
    ...
}
result = await pixelle_video.execute_with_concurrency(workflow_input, workflow_params)
```

ComfyKit 需要把这些本地文件**上传到 RunningHub**，如果上传失败或参数路由不到对应节点，RunningHub 就使用工作流默认素材。

### 2.3 对比验证

通过下载官方 `comfykit-0.1.12` 源码与本地 `.venv` 中的文件逐一对比 MD5 哈希值，确认了所有变更。

---

## 3. 精确对比结果

### 3.1 对比方法

使用 Python 脚本从 PyPI 下载官方 `comfykit-0.1.12` 源码包，解压后与本地 `.venv/Lib/site-packages/comfykit/` 中的文件逐行对比。

### 3.2 文件变更一览

| 文件 | 状态 | 变更行数 | 说明 |
|------|------|---------|------|
| `executor.py` | ✗ 已修改 | +2/-1 | 新增 `on_task_created` 参数透传 |
| `comfyui/__init__.py` | ✓ 一致 | - | - |
| `comfyui/runninghub_executor.py` | ✗ 已修改 | ~80行新增 | **核心修复** |
| `comfyui/runninghub_client.py` | ✓ 一致 | - | - |
| `comfyui/base_executor.py` | ✓ 一致 | - | - |
| `comfyui/workflow_parser.py` | ✓ 一致 | - | - |

---

## 4. 代码变更详解

### 4.1 文件一：`executor.py`

**变更**：`ComfyKit.execute()` 方法新增 `on_task_created` 参数

```python
# 官方 0.1.12
async def execute(self, workflow, params=None):
    ...

# 本地已修改
async def execute(self, workflow, params=None, on_task_created=None):
    ...
    # 第 303 行
    return await executor.execute_by_id(workflow_str, params or {}, on_task_created=on_task_created)
```

**作用**：透传 RunningHub 任务 ID 回调，支持后台取消任务功能。与文件上传问题不直接相关。

### 4.2 文件二：`runninghub_executor.py`

#### 变更 1：`execute_by_id` 新增 `on_task_created` 参数

```python
# 官方
async def execute_by_id(self, workflow_id, params=None):

# 本地
async def execute_by_id(self, workflow_id, params=None, on_task_created=None):
```

#### 变更 2：新增 `on_task_created` 回调调用

```python
# 官方（无此代码）
# 本地新增（第 119-125 行）
if on_task_created and callable(on_task_created):
    try:
        on_task_created(task_id)
    except Exception as e:
        logger.warning(f"on_task_created callback failed: {e}")
```

#### 变更 3：传递 `workflow_json` 参数

```python
# 官方
node_info_list = await self._convert_params_to_node_info_list(metadata, params, seed_changes)

# 本地
node_info_list = await self._convert_params_to_node_info_list(metadata, params, seed_changes, workflow_json)
```

函数签名同步变更：

```python
async def _convert_params_to_node_info_list(self, metadata, params, seed_changes=None, workflow_json=None):
```

#### 变更 4：⭐ 核心修复 - Fallback 自动上传逻辑

这是**解决问题的关键代码**（约 50 行），在 `_convert_params_to_node_info_list()` 方法中新增：

```python
# ===== 新增第 233-260 行：扫描工作流中的媒体上传节点 =====
MEDIA_PARAM_NAMES = {'audio', 'video', 'image'}

media_upload_nodes = []
if workflow_json is not None:
    for node_id, node_data in workflow_json.items():
        if not isinstance(node_data, dict):
            continue
        class_type = node_data.get("class_type", "")
        if class_type in MEDIA_UPLOAD_NODE_TYPES:
            # 识别：LoadImage → field_name='image'
            #      LoadAudio/VHS_LoadAudioUpload → field_name='audio'
            #      LoadVideo/VHS_LoadVideo → field_name='video'
            field_name = ...
            media_upload_nodes.append({...})
```

```python
# ===== 新增第 288-318 行：Fallback 处理未匹配的媒体参数 =====
mapped_param_names = {m.param_name for m in metadata.mapping_info.param_mappings}
for param_name, param_value in params.items():
    if param_name in mapped_param_names:
        continue  # 已通过 DSL 处理

    if param_name.lower() in MEDIA_PARAM_NAMES and media_upload_nodes:
        # 自动路由到对应媒体节点
        if 'audio' in param_name.lower():
            target = next((n for n in media_upload_nodes if 'audio' in n['class_type'].lower()), media_upload_nodes[0])
        elif 'image' in param_name.lower():
            target = next((n for n in media_upload_nodes if n['class_type'] == 'LoadImage'), media_upload_nodes[0])
        ...
        # 自动上传文件
        uploaded_value = await self._handle_runninghub_media_upload(param_value)
        node_info = {
            "nodeId": target["node_id"],
            "fieldName": target["field_name"],
            "fieldValue": uploaded_value,
        }
        node_info_list.append(node_info)
```

---

## 5. 根因分析

### 问题本质

`comfykit` 的 `_convert_params_to_node_info_list()` 方法完全依赖 **DSL 标记（`$~`）** 来识别需要上传的媒体参数。工作流解析流程：

```
workflow JSON → WorkflowParser.parse_title() → 识别 $~ 标记 → param_mapping
                                                              ↓
                                              _convert_params_to_node_info_list() 处理
```

**当 RunningHub 工作流的媒体节点没有 DSL 标记时**：

1. `WorkflowParser` 不会把该节点解析到 `param_mappings` 中
2. 参数 `{"image": "本地路径.jpg", "audio": "本地路径.mp3"}` 找不到匹配映射
3. **这些参数被静默丢弃**，文件不上传到 RunningHub
4. RunningHub 使用工作流模板中的**默认图片和音频**生成视频

### 为什么本地正常

你在 `.venv` 中修改了 `runninghub_executor.py`，添加了 **fallback 自动上传逻辑**：即使 DSL 标记缺失，也会扫描工作流 JSON 中的 `MEDIA_UPLOAD_NODE_TYPES`（`LoadImage`、`LoadAudio` 等）节点，把未匹配的 `image`/`audio` 参数自动上传并路由到对应节点。

### 为什么服务器不行

`.venv/` 是项目级虚拟环境，**不会被 git 追踪**。服务器拉取代码时不包含这些修改。

---

## 6. 解决方案

### 方案：Monkey-patch（已实施）

不依赖修改 `.venv` 中的第三方包，而是创建一个**被 git 追踪的补丁文件**，在应用启动时 monkey-patch 相关方法。

### 文件结构

```
Pixelle-Video/
├── pixelle_video/
│   ├── patches/                     # ✅ 新增 - 补丁目录
│   │   ├── __init__.py              # 包初始化
│   │   └── comfykit_patch.py        # comfykit 0.1.12 补丁
├── api/
│   └── app.py                       # ✅ 已修改 - 启动时加载补丁
```

### `pixelle_video/patches/comfykit_patch.py` 说明

| 方法 | 补丁对象 | 说明 |
|------|---------|------|
| `patch_runninghub_executor()` | `RunningHubExecutor._convert_params_to_node_info_list` | 核心修复：增加 fallback 自动上传逻辑 |
| `patch_execute_by_id()` | `RunningHubExecutor.execute_by_id` | 透传 `on_task_created` + 传递 `workflow_json` |
| `patch_executor_execute()` | `ComfyKit.execute` | 透传 `on_task_created` 参数 |

### 启动加载点

在 `api/app.py` 的 `lifespan`（应用生命周期）启动时调用：

```python
from pixelle_video.patches.comfykit_patch import apply_patches

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Pixelle-Video API...")
    apply_patches()  # ✅ 应用 comfykit monkey patches
    ...
```

补丁有版本检测，仅在 `comfykit.__version__ == "0.1.12"` 时生效，避免影响其他版本。

---

## 7. 部署步骤

### 本地

重启服务即可生效：

```bash
uv run python api/app.py
```

启动日志中会看到：

```
🔧 Applying comfykit 0.1.12 patches...
✅ Patch applied: RunningHubExecutor._convert_params_to_node_info_list
✅ Patch applied: RunningHubExecutor.execute_by_id (workflow_json passthrough)
✅ Patch applied: ComfyKit.execute (on_task_created passthrough)
✅ All comfykit patches applied
```

### 服务器

```bash
# 1. 拉取最新代码
cd /path/to/Pixelle-Video
git pull

# 2. 重启服务
supervisorctl restart pixelle-video
# 或
pm2 restart pixelle-video
# 或
systemctl restart pixelle-video
```

---

## 8. 补丁升级说明

### 何时移除补丁

当 `comfykit` 官方发布包含此修复的版本（`>=0.1.13`）时：

```bash
pip install -U comfykit>=0.1.13
```

然后删除补丁文件和引用：

```bash
git rm -r pixelle_video/patches/
```

在 `api/app.py` 中删掉：

```python
from pixelle_video.patches.comfykit_patch import apply_patches
# 以及 lifespan 中的调用
```

### 验证新版本是否包含修复

检查 `RunningHubExecutor._convert_params_to_node_info_list()` 方法中是否有 fallback 逻辑：

```python
grep -n "MEDIA_PARAM_NAMES" .venv/Lib/site-packages/comfykit/comfyui/runninghub_executor.py
grep -n "media_upload_nodes" .venv/Lib/site-packages/comfykit/comfyui/runninghub_executor.py
```

如果有输出，说明新版本已包含修复。

---

## 附录：相关文件列表

| 文件 | 作用 | 是否需要 git 追踪 |
|------|------|------------------|
| `pixelle_video/patches/__init__.py` | patches 包初始化 | ✅ 是 |
| `pixelle_video/patches/comfykit_patch.py` | comfykit 0.1.12 monkey-patch | ✅ 是 |
| `api/app.py` | 启动时加载补丁 | ✅ 是（已有） |
| `.venv/Lib/site-packages/comfykit/executor.py` | 官方包（本地已改） | ❌ 否 |
| `.venv/Lib/site-packages/comfykit/comfyui/runninghub_executor.py` | 官方包（本地已改） | ❌ 否 |