"""
comfykit 0.1.12 补丁 - RunningHub 文件上传修复

问题：
    pipelines.py 中的 _run_second_digital_workflow() 把本地文件路径
    (如 image=/path/to/xxx.jpg, audio=/path/to/narration.mp3) 传给
    ComfyKit.execute()，但 comfykit 0.1.12 的 RunningHubExecutor 无法
    将这些参数路由到工作流中的媒体上传节点（LoadImage, LoadAudio 等），
    导致文件不上传到 RunningHub，生成视频使用默认图片/音频。

修复：
    monkey-patch RunningHubExecutor._convert_params_to_node_info_list()
    方法，增加 fallback 逻辑：
    1. 扫描 worklow JSON 中所有 MEDIA_UPLOAD_NODE_TYPES 节点
    2. 对 DSL 标记未匹配到的参数（audio/video/image），自动上传后路由到
       对应媒体节点
    3. 同时修补 executor.py 透传 on_task_created 参数

用法：
    from pixelle_video.patches.comfykit_patch import apply_patches
    apply_patches()
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("comfykit.patch")

# 从 comfykit.base_executor 复制（避免 import 循环）
MEDIA_UPLOAD_NODE_TYPES = {
    'LoadImage',
    'LoadAudio',
    'LoadVideo',
    'VHS_LoadAudioUpload',
    'VHS_LoadVideo',
}


def patch_runninghub_executor():
    """修补 RunningHubExecutor._convert_params_to_node_info_list"""
    try:
        from comfykit.comfyui.runninghub_executor import RunningHubExecutor
    except ImportError:
        logger.warning("comfykit not installed, skip patch")
        return

    original_convert = RunningHubExecutor._convert_params_to_node_info_list

    async def patched_convert(self, metadata, params: dict, seed_changes: Dict[str, int] = None,
                               workflow_json: dict = None) -> List[dict]:
        """修补版 _convert_params_to_node_info_list，支持自动 fallback 上传"""
        node_info_list = []
        seed_changes = seed_changes or {}

        # 已知的无条件需要上传的参数名
        MEDIA_PARAM_NAMES = {'audio', 'video', 'image'}

        # 从原始 workflow JSON 中扫描所有媒体上传节点
        media_upload_nodes = []
        if workflow_json is not None:
            for node_id, node_data in workflow_json.items():
                if not isinstance(node_data, dict):
                    continue
                class_type = node_data.get("class_type", "")
                if class_type in MEDIA_UPLOAD_NODE_TYPES:
                    field_name = 'audio'  # 默认
                    if class_type == 'LoadImage':
                        field_name = 'image'
                    elif 'audio' in class_type.lower():
                        field_name = 'audio'
                    elif 'video' in class_type.lower():
                        field_name = 'video'
                    media_upload_nodes.append({
                        "node_id": node_id,
                        "class_type": class_type,
                        "field_name": field_name,
                    })
            if media_upload_nodes:
                logger.info(
                    "Patch: Found %d media upload nodes in workflow: %s",
                    len(media_upload_nodes),
                    [n['class_type'] for n in media_upload_nodes],
                )

        # ===== 第一步：处理 DSL 标记的映射 =====
        for param_mapping in metadata.mapping_info.param_mappings:
            param_name = param_mapping.param_name
            if param_name in params:
                param_value = params[param_name]
                node_class_type = param_mapping.node_class_type
                need_upload = param_mapping.need_upload

                if need_upload:
                    param_value = await self._handle_runninghub_media_upload(param_value)
                elif node_class_type in MEDIA_UPLOAD_NODE_TYPES:
                    param_value = await self._handle_runninghub_media_upload(param_value)

                node_info = {
                    "nodeId": param_mapping.node_id,
                    "fieldName": param_mapping.input_field,
                    "fieldValue": param_value,
                }
                node_info_list.append(node_info)
                logger.debug(f"Patch: Added nodeInfo (DSL): {node_info}")

        # ===== 第二步：fallback 处理未匹配的媒体参数 =====
        mapped_param_names = {m.param_name for m in metadata.mapping_info.param_mappings}
        for param_name, param_value in params.items():
            if param_name in mapped_param_names:
                continue  # 已通过第一步处理

            if param_name.lower() in MEDIA_PARAM_NAMES and media_upload_nodes:
                target = None
                if 'audio' in param_name.lower():
                    target = next(
                        (n for n in media_upload_nodes if 'audio' in n['class_type'].lower()),
                        media_upload_nodes[0],
                    )
                elif 'image' in param_name.lower():
                    target = next(
                        (n for n in media_upload_nodes if n['class_type'] == 'LoadImage'),
                        media_upload_nodes[0],
                    )
                else:
                    target = media_upload_nodes[0]

                uploaded_value = await self._handle_runninghub_media_upload(param_value)
                node_info = {
                    "nodeId": target["node_id"],
                    "fieldName": target["field_name"],
                    "fieldValue": uploaded_value,
                }
                node_info_list.append(node_info)
                logger.info(
                    "Patch: Auto-routed unmapped param '%s' to node %s "
                    "(class_type=%s, field=%s)",
                    param_name,
                    target["node_id"],
                    target["class_type"],
                    target["field_name"],
                )

        # ===== 第三步：处理随机种子 =====
        for node_id, seed_value in seed_changes.items():
            already_set = any(
                ni["nodeId"] == node_id and ni["fieldName"] == "seed"
                for ni in node_info_list
            )
            if not already_set:
                node_info = {
                    "nodeId": node_id,
                    "fieldName": "seed",
                    "fieldValue": seed_value,
                }
                node_info_list.append(node_info)

        return node_info_list

    # 应用 monkey patch
    RunningHubExecutor._convert_params_to_node_info_list = patched_convert
    logger.info("✅ Patch applied: RunningHubExecutor._convert_params_to_node_info_list")


def patch_executor_execute():
    """修补 ComfyKit.execute 透传 on_task_created 参数"""
    try:
        from comfykit.executor import ComfyKit
    except ImportError:
        return

    original_execute = ComfyKit.execute

    async def patched_execute(self, workflow, params=None, on_task_created=None):
        """修补版 execute，透传 on_task_created"""
        workflow_str = str(workflow)

        # RunningHub workflow ID (numeric string)
        if workflow_str.isdigit():
            executor = self._get_runninghub_executor()
            return await executor.execute_by_id(
                workflow_str, params or {}, on_task_created=on_task_created
            )

        # URL - download and execute as local
        if workflow_str.startswith(('http://', 'https://')):
            from comfykit.utils.file_util import download_files
            async with download_files(workflow_str) as temp_file_path:
                executor = self._get_local_executor()
                return await executor.execute_workflow(temp_file_path, params or {})

        # File path
        if os.path.exists(workflow_str) or '/' in workflow_str or '\\' in workflow_str:
            from comfykit.utils.runninghub_util import is_runninghub_workflow
            if os.path.exists(workflow_str) and is_runninghub_workflow(workflow_str):
                executor = self._get_runninghub_executor()
                return await executor.execute_workflow(workflow_str, params or {})
            else:
                executor = self._get_local_executor()
                return await executor.execute_workflow(workflow_str, params or {})

        # Unknown - try as file path
        executor = self._get_local_executor()
        return await executor.execute_workflow(workflow_str, params or {})

    ComfyKit.execute = patched_execute
    logger.info("✅ Patch applied: ComfyKit.execute (on_task_created passthrough)")


def patch_execute_by_id():
    """修补 RunningHubExecutor.execute_by_id 接受 on_task_created"""
    try:
        from comfykit.comfyui.runninghub_executor import RunningHubExecutor
    except ImportError:
        return

    original_execute_by_id = RunningHubExecutor.execute_by_id

    async def patched_execute_by_id(self, workflow_id, params=None, on_task_created=None):
        """修补版 execute_by_id，接受 on_task_created 并传递 workflow_json"""
        import asyncio
        import time

        start_time = asyncio.get_event_loop().time()
        logger.info(f"Patch: Starting RunningHub workflow: workflow_id={workflow_id}")

        # 获取 workflow JSON
        workflow_json = await self.client.get_workflow_json(workflow_id)

        # 随机种子
        workflow_json, seed_changes = self._randomize_seed_in_workflow(workflow_json)

        # 解析参数
        from comfykit.comfyui.workflow_parser import WorkflowParser
        parser = WorkflowParser()
        metadata = parser.parse_workflow(workflow_json, f"workflow_{workflow_id}")

        if not metadata:
            from comfykit.comfyui.models import ExecuteResult
            return ExecuteResult(status="error", msg="Failed to parse workflow metadata")

        metadata.workflow_id = workflow_id
        metadata.is_runninghub = True

        logger.info(f"Patch: Workflow parsed: {len(metadata.params)} params")

        # 转换参数 - 传入 workflow_json 以支持 fallback 上传
        node_info_list = await self._convert_params_to_node_info_list(
            metadata, params or {}, seed_changes, workflow_json
        )

        # 提取输出节点
        output_id_2_var = self._extract_output_nodes(metadata)

        # 创建任务
        task_data = await self.client.create_task(
            workflow_id, node_info_list if node_info_list else None
        )
        task_id = task_data.get('taskId')
        if not task_id:
            from comfykit.comfyui.models import ExecuteResult
            return ExecuteResult(status="error", msg="Failed to create RunningHub task")

        logger.info(f"Patch: RunningHub task created: {task_id}")

        # 回调
        if on_task_created and callable(on_task_created):
            try:
                on_task_created(task_id)
            except Exception as e:
                logger.warning(f"Patch: on_task_created callback failed: {e}")

        # 等待完成
        result = await self._wait_for_task_completion(task_id, output_id_2_var)
        end_time = asyncio.get_event_loop().time()
        result.duration = end_time - start_time
        return result

    RunningHubExecutor.execute_by_id = patched_execute_by_id
    logger.info("✅ Patch applied: RunningHubExecutor.execute_by_id (workflow_json passthrough)")


def apply_patches():
    """应用所有 comfykit 补丁"""
    # 仅在 comfykit 0.1.12 时应用补丁
    try:
        import comfykit
        ver = getattr(comfykit, "__version__", "unknown")
        if ver != "0.1.12":
            logger.info(f"comfykit version is {ver}, patches designed for 0.1.12, skipping")
            return
    except ImportError:
        logger.warning("comfykit not installed, skip patches")
        return

    logger.info("🔧 Applying comfykit 0.1.12 patches...")
    patch_runninghub_executor()
    patch_execute_by_id()
    patch_executor_execute()
    logger.info("✅ All comfykit patches applied")