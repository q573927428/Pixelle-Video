<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 左列 ====== -->
    <div class="form-column">

      <!-- ====== 第一板块：人物形象上传 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
        <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
          <span>🧑 人物上传</span>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:13px;font-weight:400;">批量</span>
            <el-switch v-model="form.batch_mode" @change="onBatchModeChange" />
            <span class="vip-badge" v-if="!auth.isVip.value && !auth.isSvip.value && !auth.isAdmin.value" @click="handleVipBadgeClick">👑 VIP</span>
          </div>
        </div>
        <div class="form-section-body">
        <template v-if="form.batch_mode">
          <el-alert
            title="可上传多张人物图片，按顺序与文案一一对应；少于文案数时最后一张循环使用"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom:14px;"
          />
          <el-form-item label="人物图片（按顺序一一对应）">
            <div class="upload-field-container">
              <UploadBox category="character_image" accept="image/*,.heic,.heif" @upload="(f, c) => $emit('upload', f, c, 'digital_batch_character')" @select-history="(c) => $emit('select-history', c)" />
            </div>
            <div v-if="form.batch_character_assets.length > 0" style="width:100%;">
              <div class="small muted" style="margin-bottom:6px;">
                已上传 {{ form.batch_character_assets.length }} 张人物图片
              </div>
              <FilePreview :items="form.batch_character_assets" @remove="(idx) => form.batch_character_assets.splice(idx, 1)" />
            </div>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="角色图片">
            <div class="upload-field-container">
              <UploadBox category="character_image" accept="image/*,.heic,.heif" @upload="(f, c) => $emit('upload', f, c, 'digital_character')" @select-history="(c) => $emit('select-history', c)" />
              <FilePreview v-if="form.character_asset" :items="[form.character_asset]" @remove="form.character_asset = null" />
            </div>
          </el-form-item>
        </template>
      </div>
        </div>
      </div>

      <!-- ====== 第二板块：配音合成 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
        <div class="form-section-title">🎤 配音合成</div>
        <div class="form-section-body">
        <el-form-item>
          <el-radio-group v-model="form.tts_inference_mode">
            <el-radio-button value="comfyui">克隆声音</el-radio-button>
            <el-radio-button value="local">内置语音</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 本地模式：可切换 Edge TTS / VoxCPM API -->
        <div v-if="form.tts_inference_mode === 'local'" class="soft-panel">
          <!-- <el-form-item label="本地 TTS 引擎">
            <el-radio-group v-model="form.tts_engine">
              <el-radio-button value="edge_tts">Edge TTS（默认）</el-radio-button>
              <el-radio-button value="voxcpm_api">VoxCPM API（在线）</el-radio-button>
            </el-radio-group>
          </el-form-item> -->

          <!-- Edge TTS 选项 -->
          <div v-if="form.tts_engine === 'edge_tts'">
            <el-form-item label="音色选择">
              <el-select v-model="form.tts_voice" filterable placeholder="选择 TTS 音色" style="width:100%;">
                <el-option
                  v-for="voice in ttsVoices"
                  :key="voice.id"
                  :label="voice.name"
                  :value="voice.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="语速">
              <el-slider v-model="form.tts_speed" :min="0.5" :max="2.0" :step="0.1" show-input />
            </el-form-item>
          </div>

          <!-- VoxCPM API 选项 -->
          <div v-if="form.tts_engine === 'voxcpm_api'" class="voxcpm-section">
            <!-- <el-form-item label="CFG 强度">
              <el-slider v-model="form.voxcpm_cfg" :min="1.0" :max="3.0" :step="0.1" show-input />
            </el-form-item> -->
            <!-- <el-form-item label="控制指令">
              <el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔" />
            </el-form-item> -->
            <!-- <div class="checkbox-row">
              <el-checkbox v-model="form.voxcpm_normalize">归一化 Normalize</el-checkbox>
              <el-checkbox v-model="form.voxcpm_denoise">降噪 Denoise</el-checkbox>
            </div> -->
              <el-form-item label="参考音频">
              <div class="upload-field-container">
                <UploadBox category="ref_audio" accept="audio/*,.amr" @upload="(f, c) => $emit('upload', f, c, 'digital_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
                <FilePreview v-if="form.ref_audio" :items="refAudioItems" @remove="form.ref_audio = ''" />
              </div>
            </el-form-item>
            <div v-if="form.ref_audio" class="soft-panel">
              <el-checkbox v-model="form.voxcpm_use_prompt_text">启用 Prompt Text</el-checkbox>
              <el-form-item v-if="form.voxcpm_use_prompt_text" label="Prompt Text">
                <div style="position:relative;width:100%;">
                  <el-input
                    v-model="form.voxcpm_prompt_text"
                    type="textarea"
                    :rows="2"
                    placeholder="参考音频的文字内容"
                    style="width:100%;"
                  />
                  <el-button
                    circle
                    type="primary"
                    size="small"
                    @click="handleAsrTranscribe"
                    :loading="asrLoading"
                    :disabled="!form.ref_audio"
                    style="position:absolute;bottom:6px;right:6px;z-index:1;"
                  >
                    🎙️
                  </el-button>
                </div>
              </el-form-item>
            </div>
          </div>
        </div>

        <!-- ComfyUI 模式 -->
        <div v-if="form.tts_inference_mode === 'comfyui'" class="soft-panel">
          <!-- <el-form-item label="TTS 工作流">
            <el-select v-model="form.tts_workflow" filterable clearable placeholder="选择 TTS 工作流" style="width:100%;">
              <el-option v-for="wf in ttsWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item> -->
          <el-form-item label="参考音频">
            <div class="upload-field-container">
               <UploadBox category="ref_audio" accept="audio/*,.amr" @upload="(f, c) => $emit('upload', f, c, 'digital_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
              <FilePreview v-if="form.ref_audio" :items="refAudioItems" @remove="form.ref_audio = ''" />
            </div>
          </el-form-item>
        </div>

        <!-- 声音预览（默认折叠） -->
        <el-collapse v-model="previewActiveNames" style="margin-top:12px;">
          <el-collapse-item name="voice-preview">
            <template #title>
              <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🔊 声音预览</span>
            </template>
            <el-input v-model="previewText" type="textarea" :rows="2" placeholder="大家好，这是一段测试语音。" :maxlength="30" show-word-limit style="margin-bottom:8px;" />
            <div style="display:flex;gap:10px;align-items:center;">
              <el-button type="primary" @click="handlePreviewTts" :loading="previewLoading">
                ▶ 生成预览
              </el-button>
              <audio v-if="previewAudioUrl" :src="previewAudioUrl" controls style="height:32px;flex:1;min-width:0;" />
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
        </div>
      </div>

    </div>

    <!-- ====== 右列 ====== -->
    <div class="form-column">

      <!-- ====== 第三板块：生成模式 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
        <div class="form-section-title">💫 选择生成模式</div>
        <div class="form-section-body">

        <!-- 模式选择：始终可见 -->
        <el-form-item label="模式">
          <el-radio-group v-model="form.mode">
            <el-radio-button value="customize">🧐 口播模式</el-radio-button>
            <el-radio-button value="digital">💻 带货模式</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- ====== 批量模式：多组数据输入 ====== -->
        <template v-if="form.batch_mode">
          <!-- 批量-带货模式 -->
          <template v-if="form.mode === 'digital'">
            <el-alert
              title="每行输入一个商品主题/标题，按顺序对应商品图片（可选）"
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom:14px;"
            />
            <el-form-item label="商品主题列表（每行一个）">
              <el-input
                v-model="form.batch_topics"
                type="textarea"
                :rows="8"
                placeholder="智能保温杯&#10;无线蓝牙耳机&#10;便携式咖啡机&#10;..."
              />
            </el-form-item>
            <div v-if="batchTopicsCount > 0" class="soft-panel">
              <el-tag :type="batchExceedLimit ? 'danger' : 'success'">
                共 {{ batchTopicsCount }} 个主题
                <template v-if="batchExceedLimit">（最多 10 个）</template>
              </el-tag>
              <el-alert
                v-if="batchExceedLimit"
                title="批量模式最多支持 10 个主题，请减少数量"
                type="error"
                :closable="false"
                show-icon
                style="margin-top:8px;"
              />
              <div class="small muted" style="margin-top:6px;">
                商品标题使用主题名称，文案由 AI 自动生成。
                可上传多张商品图片，按顺序与主题一一对应；少于主题数时最后一张循环使用。
              </div>
              <div v-if="overLimitLines.length > 0" style="margin-top:6px;">
                <el-tag v-for="idx in overLimitLines" :key="idx" type="danger" size="small" style="margin-right:4px;margin-bottom:4px;">
                  第 {{ idx }} 行超 {{ textMaxLength }} 字
                </el-tag>
              </div>
            </div>
            <el-form-item label="商品图片（按顺序一一对应）">
              <div class="upload-field-container">
                <UploadBox category="goods_image" accept="image/*,.heic,.heif" @upload="(f, c) => $emit('upload', f, c, 'digital_batch_goods')" @select-history="(c) => $emit('select-history', c)" />
              </div>
              <div v-if="form.batch_goods_assets.length > 0" style="width:100%;">
                <div class="small muted" style="margin-bottom:6px;">
                  已上传 {{ form.batch_goods_assets.length }} 张商品图片
                </div>
                <FilePreview :items="form.batch_goods_assets" @remove="(idx) => form.batch_goods_assets.splice(idx, 1)" />
              </div>
            </el-form-item>
          </template>

          <!-- 批量-自定义模式 -->
          <template v-if="form.mode === 'customize'">
            <el-alert
              title="每行输入一段固定口播文案，系统逐行生成数字人视频"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom:14px;"
            />
            <el-form-item label="口播文案列表（每行一段）">
              <el-input
                v-model="form.batch_topics"
                type="textarea"
                :rows="10"
                placeholder="这件商品真的太好用了，推荐给大家。&#10;今天给大家带来一款超实用的产品，看完你就懂了。&#10;你可能不知道，这款产品还有这么多隐藏功能。&#10;..."
              />
            </el-form-item>
            <div v-if="batchTopicsCount > 0" class="soft-panel">
              <el-tag :type="batchExceedLimit ? 'danger' : 'success'">
                共 {{ batchTopicsCount }} 段文案
                <template v-if="batchExceedLimit">（最多 10 段）</template>
              </el-tag>
              <el-alert
                v-if="batchExceedLimit"
                title="批量模式最多支持 10 段文案，请减少数量"
                type="error"
                :closable="false"
                show-icon
                style="margin-top:8px;"
              />
              <div class="small muted" style="margin-top:6px;">每段文案对应一个口播视频</div>
              <div v-if="overLimitLines.length > 0" style="margin-top:6px;">
                <el-tag v-for="idx in overLimitLines" :key="idx" type="danger" size="small" style="margin-right:4px;margin-bottom:4px;">
                  第 {{ idx }} 行超 {{ textMaxLength }} 字
                </el-tag>
              </div>
            </div>
          </template>
        </template>

        <!-- ====== 单次模式：常规输入 ====== -->
        <template v-if="!form.batch_mode">
          <!-- 带货模式 -->
          <div v-if="form.mode === 'digital'" class="soft-panel">
            <el-form-item label="商品图片">
              <div class="upload-field-container">
                <UploadBox category="goods_image" accept="image/*,.heic,.heif" @upload="(f, c) => $emit('upload', f, c, 'digital_goods')" @select-history="(c) => $emit('select-history', c)" />
                <FilePreview v-if="form.goods_asset" :items="[form.goods_asset]" @remove="form.goods_asset = null" />
              </div>
            </el-form-item>
            <el-form-item label="商品标题">
              <el-input v-model="form.goods_title" placeholder="例如：智能保温杯" :maxlength="30" show-word-limit />
            </el-form-item>
            <el-form-item label="口播文案（可留空自动生成）">
              <el-input v-model="form.goods_text" type="textarea" :rows="5" :maxlength="textMaxLength" show-word-limit placeholder="可填写固定口播文案；留空时 AI 自动根据商品标题生成" />
            </el-form-item>
          </div>

          <!-- 自定义模式 -->
          <div v-if="form.mode === 'customize'" class="soft-panel">
            <el-form-item label="自定义口播文案">
              <el-input v-model="form.goods_text" type="textarea" :rows="6" :maxlength="textMaxLength" show-word-limit placeholder="填写固定口播文案内容" />
              <div style="margin-top:8px;display:flex;gap:8px;justify-content:flex-end;">
                <el-button v-if="form.goods_text.trim()" type="warning" size="small" @click="handleRewrite" :loading="rewriteLoading">
                  ✨ 一键改写
                </el-button>
                <el-button type="primary" size="small" @click="mediaDialogVisible = true">
                  🎵 从短视频链接提取
                </el-button>
              </div>
            </el-form-item>
          </div>

          <!-- 短视频导入弹窗 -->
          <el-dialog v-model="mediaDialogVisible" title="从短视频导入口播文案" :close-on-click-modal="false" class="media-dialog">
            <div style="margin-bottom:12px;font-size:13px;color:var(--el-text-color-secondary);">
              粘贴抖音/快手/小红书/B站等短视频分享信息，系统将自动提取视频中的口播文案。
            </div>
            <el-input
              v-model="mediaShareText"
              type="textarea"
              :rows="8"
              placeholder="粘贴短视频分享链接/信息&#10;&#10;支持：抖音、快手、小红书、B站&#10;例如：https://v.douyin.com/OOgNGe6Ln20/"
            />
            <template #footer>
              <el-button @click="handlePasteFromClipboard">📋 粘贴</el-button>
              <el-button @click="mediaDialogVisible = false">取消</el-button>
              <el-button
                type="primary"
                @click="handleMediaParse"
                :loading="mediaLoading"
                :disabled="!mediaShareText.trim()"
              >
                解析并导入
              </el-button>
            </template>
          </el-dialog>
        </template>
      </div>
        </div>
      </div>

      <!-- ====== 第四板块：服务配置（注释保留） ====== -->
      <div class="form-section-wrapper" v-if="false">
        <div class="form-section">
        <div class="form-section-title">⚙️ 服务配置</div>
        <div class="form-section-body">

        <!-- 3.1 前置图片生成服务 -->
        <div class="sub-section">
          <div class="sub-section-title">3.1 前置图片生成服务来源</div>
          <el-form-item >
            <el-radio-group v-model="form.image_service_mode">
              <el-radio-button value="runninghub">☁️ RunningHub（云端）</el-radio-button>
              <el-radio-button value="api">API 模型</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <!-- RunningHub 模式 -->
          <div v-if="form.image_service_mode === 'runninghub'" class="soft-panel">
            <el-form-item label="工作流">
              <el-select v-model="form.workflow_config.first_workflow_path" filterable placeholder="选择 RunningHub 工作流" style="width:100%;">
                <el-option
                  v-for="wf in imageWorkflows"
                  :key="wf.key"
                  :label="wf.display_name"
                  :value="wf.key"
                />
              </el-select>
            </el-form-item>
          </div>

          <!-- API 模型模式 -->
          <div v-if="form.image_service_mode === 'api'" class="soft-panel">
            <el-form-item label="API 模型">
              <el-select v-model="form.image_api_model" filterable placeholder="选择 API 图片模型" style="width:100%;">
                <el-option label="wan2.7-image - API Dashscope" value="dashscope/wan2.7-image" />
                <el-option label="wan2.7-image-pro - API Dashscope" value="dashscope/wan2.7-image-pro" />
                <el-option label="wan2.6-t2i - API Dashscope" value="dashscope/wan2.6-t2i" />
                <el-option label="gpt-image-2 - API OpenAI" value="openai/gpt-image-2" />
                <el-option label="doubao-seedream-5-0-260128 - API Seedream" value="seedream/doubao-seedream-5-0-260128" />
                <el-option label="doubao-seedream-4-5-251128 - API Seedream" value="seedream/doubao-seedream-4-5-251128" />
                <el-option label="doubao-seedream-4-0-250828 - API Seedream" value="seedream/doubao-seedream-4-0-250828" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <!-- 3.2 口播视频合成服务 -->
        <div class="sub-section">
          <div class="sub-section-title">3.2 口播视频合成服务来源</div>
          <el-form-item>
            <el-radio-group v-model="form.video_service_mode">
              <el-radio-button value="runninghub">☁️ RunningHub（云端）</el-radio-button>
              <el-radio-button value="api">API 模型</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <!-- RunningHub 模式 -->
          <div v-if="form.video_service_mode === 'runninghub'" class="soft-panel">
            <el-form-item label="工作流">
              <el-select v-model="form.workflow_config.second_workflow_path" filterable placeholder="选择 RunningHub 工作流" style="width:100%;">
                <el-option
                  v-for="wf in videoWorkflows"
                  :key="wf.key"
                  :label="wf.display_name"
                  :value="wf.key"
                />
              </el-select>
            </el-form-item>
          </div>

          <!-- API 模型模式 -->
          <div v-if="form.video_service_mode === 'api'" class="soft-panel">
            <el-form-item label="API 模型">
              <el-select v-model="form.video_api_model" filterable placeholder="选择 API 视频模型" style="width:100%;">
                <el-option label="wan2.7-r2v - API Dashscope" value="dashscope/wan2.7-r2v" />
                <el-option label="happyhorse-1.0-r2v - API Dashscope" value="dashscope/happyhorse-1.0-r2v" />
              </el-select>
            </el-form-item>

            <el-collapse v-model="videoApiParamsActiveNames" style="margin-top:12px;">
              <el-collapse-item name="video-api-params">
                <template #title>
                  <span class="sub-section-title" style="font-size:13px;">API 视频模型参数</span>
                </template>
                <el-form-item label="已接入能力">
                  <el-tag type="info">digital_human</el-tag>
                  <el-tag type="info" style="margin-left:6px;">reference_to_video</el-tag>
                  <el-tag type="info" style="margin-left:6px;">voice_reference</el-tag>
                </el-form-item>
                <el-form-item label="视频时长（秒）">
                  <el-input-number v-model="form.video_api_params.duration" :min="5" :max="15" :step="1" style="width:100%;" />
                </el-form-item>
                <el-form-item label="分辨率">
                  <el-select v-model="form.video_api_params.resolution" filterable placeholder="选择分辨率" style="width:100%;">
                    <el-option label="720P（默认）" value="1280x720" />
                    <el-option label="1080P" value="1920x1080" />
                  </el-select>
                </el-form-item>
                <el-form-item label="画幅比例">
                  <el-select v-model="form.video_api_params.aspect_ratio" filterable placeholder="选择画幅比例" style="width:100%;">
                    <el-option label="9:16（默认）" value="9:16" />
                    <el-option label="16:9" value="16:9" />
                    <el-option label="1:1" value="1:1" />
                    <el-option label="4:3" value="4:3" />
                    <el-option label="3:4" value="3:4" />
                  </el-select>
                </el-form-item>
                <el-form-item label="负向提示词（可选）">
                  <el-input v-model="form.video_api_params.negative_prompt" type="textarea" :rows="2" placeholder="输入不希望出现的内容" />
                </el-form-item>
                <el-form-item>
                  <el-checkbox v-model="form.video_api_params.watermark">添加水印</el-checkbox>
                </el-form-item>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>
        </div>
      </div>
      <!-- ====== 字幕配置 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
          <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
            <span>📝 字幕配置</span>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-size:13px;font-weight:400;">开关</span>
              <el-switch v-model="form.subtitle_enabled" @change="onSubtitleEnabledChange" />
              <span class="vip-badge" v-if="!auth.isVip.value && !auth.isSvip.value && !auth.isAdmin.value" @click="handleVipBadgeClick">👑 VIP</span>
            </div>
          </div>
          <div class="form-section-body" v-if="form.subtitle_enabled">
            <el-collapse v-model="subtitleActiveNames">
              <el-collapse-item name="subtitle-basic">
                <template #title>
                  <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">📐 普通设置</span>
                </template>
                <el-form-item label="文字大小">
                  <el-slider v-model="form.subtitle_config.font_size" :min="22" :max="96" :step="2" show-input />
                </el-form-item>
                <el-form-item label="文字颜色">
                  <el-color-picker v-model="form.subtitle_config.font_color" show-alpha />
                </el-form-item>
                <el-form-item label="文字间距">
                  <el-slider v-model="form.subtitle_config.letter_spacing" :min="0" :max="50" :step="1" show-input />
                </el-form-item>
                <el-divider style="margin:8px 0;" />
                <el-form-item label="文字边框粗细">
                  <el-slider v-model="form.subtitle_config.font_border_width" :min="0" :max="10" :step="1" show-input />
                </el-form-item>
                <el-form-item label="文字边框颜色">
                  <el-color-picker v-model="form.subtitle_config.font_border_color" show-alpha />
                </el-form-item>
                <el-divider style="margin:8px 0;" />
                <el-form-item label="位置 X">
                  <el-slider v-model="form.subtitle_config.position_x" :min="-500" :max="500" :step="10" show-input />
                </el-form-item>
                <el-form-item label="位置 Y">
                  <el-slider v-model="form.subtitle_config.position_y" :min="-1700" :max="100" :step="10" show-input />
                </el-form-item>
              </el-collapse-item>
              <div style="height:15px;"></div>
              <el-collapse-item name="subtitle-advanced">
                <template #title>
                  <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">⚙️ 高级设置</span>
                </template>
                <el-form-item label="最大宽度">
                  <el-slider v-model="form.subtitle_config.max_width" :min="100" :max="1980" :step="20" show-input />
                </el-form-item>
                <el-divider style="margin:8px 0;" />
                <el-form-item label="背景颜色">
                  <el-color-picker v-model="form.subtitle_config.background_color" show-alpha />
                </el-form-item>
                <el-form-item label="背景透明度">
                  <el-slider v-model="form.subtitle_config.background_opacity" :min="0" :max="1.0" :step="0.1" show-input />
                </el-form-item>
                <el-form-item label="背景内边距">
                  <el-input v-model="form.subtitle_config.background_padding" placeholder="例如：10 20（上下 左右） 或 10 20 10 20（上 右 下 左）" />
                  <small>例如：10 20（上下 左右） 或 10 20 10 20（上 右 下 左）</small>
                </el-form-item>
                <el-form-item label="背景圆角">
                  <el-input-number v-model="form.subtitle_config.background_radius" :min="0" :max="50" :step="2" style="width:100%;" />
                </el-form-item>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>

    </div>
  </el-form>
  <VipPurchaseDialog ref="vipDialogRef" />
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { DigitalForm, WorkflowInfo, TtsVoiceInfo } from '../types'
import { request, filePreviewUrl } from '../api'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'
import VipPurchaseDialog from './VipPurchaseDialog.vue'
import { ElMessage } from 'element-plus'
import { getAuth } from '../composables/useAuth'

const auth = getAuth()
const vipDialogRef = ref<InstanceType<typeof VipPurchaseDialog> | null>(null)

function handleVipBadgeClick() {
  vipDialogRef.value?.openVipDialog()
}
const textMaxLength = computed(() => (auth.isVip.value || auth.isSvip.value || auth.isAdmin.value) ? 398 : 150)
const BATCH_MAX_COUNT = 10

const props = defineProps<{
  form: DigitalForm
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
  ttsVoices: TtsVoiceInfo[]
}>()

const refAudioItems = computed<string[]>(() => {
  return props.form.ref_audio ? [props.form.ref_audio] : []
})

// 批量模式：计算主题数量
const batchTopicsCount = computed(() => {
  if (!props.form.batch_topics || !props.form.batch_topics.trim()) return 0
  return props.form.batch_topics.trim().split('\n').filter(line => line.trim()).length
})

// 批量模式：是否超过最大限制
const batchExceedLimit = computed(() => {
  return batchTopicsCount.value > BATCH_MAX_COUNT
})

// 批量模式：超出字数限制的行号（1-based，跳过空行）
const overLimitLines = computed(() => {
  if (!props.form.batch_topics || !props.form.batch_topics.trim()) return []
  const lines = props.form.batch_topics.split('\n')
  const maxLen = textMaxLength.value
  const result: number[] = []
  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    if (trimmed && trimmed.length > maxLen) {
      result.push(idx + 1)
    }
  })
  return result
})

// 从 mediaWorkflows 中过滤出图片生成相关的工作流（来源为 runninghub）
const imageWorkflows = computed<WorkflowInfo[]>(() => {
  return props.mediaWorkflows.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    return wf.source === 'runninghub' && (key.includes('image') || key.includes('digital_image'))
  })
})

// 从 mediaWorkflows 中过滤出口播视频合成相关的工作流（来源为 runninghub）
const videoWorkflows = computed<WorkflowInfo[]>(() => {
  return props.mediaWorkflows.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    return wf.source === 'runninghub' && (key.includes('combination') || key.includes('digital_combination') || key.includes('video'))
  })
})

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

// 批量模式下不强制切换模式，两种模式都支持
function onBatchModeChange(val: boolean) {
  if (!val) return
  if (!auth.isVip.value && !auth.isSvip.value && !auth.isAdmin.value) {
    props.form.batch_mode = false
    ElMessage.warning('批量模式为 VIP 会员专属功能，请升级会员后使用')
  }
}

function onSubtitleEnabledChange(val: boolean) {
  if (!val) return
  if (!auth.isVip.value && !auth.isSvip.value && !auth.isAdmin.value) {
    props.form.subtitle_enabled = false
    ElMessage.warning('字幕功能为 VIP 会员专属功能，请升级会员后使用')
  }
}

const videoApiParamsActiveNames = ref<string[]>([])

const subtitleActiveNames = ref<string[]>(['subtitle-basic'])

// === 实时字幕预览 Canvas ===
const previewCanvasRef = ref<HTMLCanvasElement | null>(null)
const CANVAS_PREVIEW_WIDTH = 360  // 预览 Canvas 宽度（模拟 1080p 等比缩放）
const CANVAS_PREVIEW_HEIGHT = 640 // 预览 Canvas 高度（9:16 竖屏）
const canvasWidth = computed(() => CANVAS_PREVIEW_WIDTH)
const canvasHeight = computed(() => CANVAS_PREVIEW_HEIGHT)

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function renderSubtitlePreview() {
  const canvas = previewCanvasRef.value
  if (!canvas) return
  const cfg = props.form.subtitle_config
  if (!cfg) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // 缩放比例：从 1080x1920 缩放到 Canvas 尺寸
  const scaleX = CANVAS_PREVIEW_WIDTH / 1080
  const scaleY = CANVAS_PREVIEW_HEIGHT / 1920
  const scale = Math.min(scaleX, scaleY)

  // 清空画布
  ctx.clearRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)

  // 绘制深色背景模拟视频
  ctx.fillStyle = '#1a1a2e'
  ctx.fillRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)

  // 预览时只取第一句文案显示
  let rawText = props.form.goods_text?.trim() || '这是一个字幕样式预览'
  if (rawText.length > 3) {
    const sentences = rawText.split(/(?<=[。！？；，.!?;\s])/)
    rawText = sentences[0] || rawText
  }
  const demoText = rawText

  // 计算缩放后的参数
  const fontSize = Math.round(cfg.font_size * scale)
  const maxWidth = Math.round(cfg.max_width * scale)
  const offsetX = Math.round(cfg.position_x * scale)
  const offsetY = Math.round(cfg.position_y * scale)
  const radius = Math.round(cfg.background_radius * scale)

  // 解析 padding
  const padParts = (cfg.background_padding || '10 20').split(' ').map(Number)
  let padT = 10, padR = 20, padB = 10, padL = 20
  if (padParts.length === 1) { padT = padR = padB = padL = padParts[0] }
  else if (padParts.length === 2) { padT = padB = padParts[0]; padR = padL = padParts[1] }
  else if (padParts.length === 4) { padT = padParts[0]; padR = padParts[1]; padB = padParts[2]; padL = padParts[3] }
  padT = Math.round(padT * scale); padR = Math.round(padR * scale)
  padB = Math.round(padB * scale); padL = Math.round(padL * scale)

  // 设置字体
  ctx.font = `${fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
  ctx.textBaseline = 'top'

  // 文字边框
  const borderWidth = Math.round((cfg.font_border_width || 0) * scale)
  const borderColor = cfg.font_border_color || '#000000'

  // 文字间距（缩放后）
  const letterSpacing = Math.round((cfg.letter_spacing || 0) * scale)

  // 计算带间距的文本宽度
  const ctxSafe = ctx as CanvasRenderingContext2D
  function getLineWidth(txt: string): number {
    if (!txt) return 0
    if (letterSpacing > 0 && txt.length > 1) {
      return ctxSafe.measureText(txt).width + letterSpacing * (txt.length - 1)
    }
    return ctxSafe.measureText(txt).width
  }

  // 重新计算文字行（考虑文字间距）
  const lines: string[] = []
  let curLine = ''
  for (const char of demoText) {
    const test = curLine + char
    if (getLineWidth(test) > maxWidth && curLine) {
      lines.push(curLine)
      curLine = char
    } else {
      curLine = test
    }
  }
  if (curLine) lines.push(curLine)

  // 行高
  const lineHeight = fontSize + Math.round(4 * scale)

  // 背景尺寸（使用带间距的宽度）
  const lineWidths = lines.map(l => getLineWidth(l))
  const maxLineWidth = Math.max(...lineWidths)
  const bgWidth = maxLineWidth + padL + padR
  const bgHeight = lines.length * lineHeight + padT + padB

  // 位置（基座在底部上方）
  const baseX = CANVAS_PREVIEW_WIDTH / 2 + offsetX
  const baseY = CANVAS_PREVIEW_HEIGHT - 100 * scale + offsetY
  const bgX = baseX - bgWidth / 2
  const bgY = baseY - bgHeight

  // 绘制圆角背景（用新尺寸）
  ctxSafe.clearRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)
  ctxSafe.fillStyle = '#1a1a2e'
  ctxSafe.fillRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)

  const bgAlpha = Math.max(0, Math.min(1, cfg.background_opacity))
  ctxSafe.fillStyle = hexToRgba(cfg.background_color, bgAlpha)
  const r = Math.min(radius, bgHeight / 2, bgWidth / 2)
  if (r > 0) {
    ctxSafe.beginPath()
    ctxSafe.moveTo(bgX + r, bgY)
    ctxSafe.lineTo(bgX + bgWidth - r, bgY)
    ctxSafe.quadraticCurveTo(bgX + bgWidth, bgY, bgX + bgWidth, bgY + r)
    ctxSafe.lineTo(bgX + bgWidth, bgY + bgHeight - r)
    ctxSafe.quadraticCurveTo(bgX + bgWidth, bgY + bgHeight, bgX + bgWidth - r, bgY + bgHeight)
    ctxSafe.lineTo(bgX + r, bgY + bgHeight)
    ctxSafe.quadraticCurveTo(bgX, bgY + bgHeight, bgX, bgY + bgHeight - r)
    ctxSafe.lineTo(bgX, bgY + r)
    ctxSafe.quadraticCurveTo(bgX, bgY, bgX + r, bgY)
    ctxSafe.closePath()
    ctxSafe.fill()
  } else {
    ctxSafe.fillRect(bgX, bgY, bgWidth, bgHeight)
  }

  // 绘制文字（每行居中，与后端 Pillow 渲染一致）
  ctxSafe.fillStyle = cfg.font_color || '#FFFFFF'
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const y = bgY + padT + i * lineHeight
    const lineWidth = getLineWidth(line)
    // 每行在背景框内居中
    const startX = bgX + (bgWidth - lineWidth) / 2
    if (letterSpacing > 0 && line.length > 1) {
      let currentX = startX
      for (const char of line) {
        if (borderWidth > 0) {
          ctxSafe.strokeStyle = borderColor
          ctxSafe.lineWidth = borderWidth
          ctxSafe.lineJoin = 'round'
          ctxSafe.miterLimit = 2
          ctxSafe.strokeText(char, currentX, y)
        }
        ctxSafe.fillText(char, currentX, y)
        currentX += ctxSafe.measureText(char).width + letterSpacing
      }
    } else {
      if (borderWidth > 0) {
        ctxSafe.strokeStyle = borderColor
        ctxSafe.lineWidth = borderWidth
        ctxSafe.lineJoin = 'round'
        ctxSafe.miterLimit = 2
        ctxSafe.strokeText(line, startX, y)
      }
      ctxSafe.fillText(line, startX, y)
    }
  }
}

// 监听字幕配置变化，重新渲染预览 Canvas
watch(
  () => [
    props.form.subtitle_config.font_size,
    props.form.subtitle_config.font_color,
    props.form.subtitle_config.position_x,
    props.form.subtitle_config.position_y,
    props.form.subtitle_config.max_width,
    props.form.subtitle_config.letter_spacing,
    props.form.subtitle_config.background_color,
    props.form.subtitle_config.background_opacity,
    props.form.subtitle_config.background_padding,
    props.form.subtitle_config.background_radius,
    props.form.subtitle_config.font_border_width,
    props.form.subtitle_config.font_border_color,
  ],
  () => {
    nextTick(renderSubtitlePreview)
  },
  { immediate: true, deep: true }
)

const previewActiveNames = ref<string[]>([])
const asrLoading = ref(false)

// 声音预览
const previewText = ref('大家好，这是一段测试语音。')
const previewLoading = ref(false)
const previewAudioUrl = ref('')

async function handlePreviewTts() {
  if (!previewText.value.trim()) {
    ElMessage.warning('请输入预览文本')
    return
  }
  previewLoading.value = true
  previewAudioUrl.value = ''
  try {
    const params: Record<string, any> = { text: previewText.value.trim() }
    
    if (props.form.tts_inference_mode === 'local') {
      if (props.form.tts_engine === 'voxcpm_api') {
        // VoxCPM API: 直接调用 VoxCPM，不走 ComfyUI/workflow
        params.engine = 'voxcpm_api'
        if (props.form.voxcpm_cfg) params.cfg = props.form.voxcpm_cfg
        if (props.form.voxcpm_normalize) params.normalize = true
        if (props.form.voxcpm_denoise) params.denoise = true
        if (props.form.voxcpm_control_instruction) params.control_instruction = props.form.voxcpm_control_instruction
        if (props.form.voxcpm_use_prompt_text) {
          params.use_prompt_text = true
          if (props.form.voxcpm_prompt_text) params.prompt_text = props.form.voxcpm_prompt_text
        }
        if (props.form.ref_audio) {
          params.ref_audio = props.form.ref_audio
        }
      } else {
        // Edge TTS: 使用 voice_id 选择音色
        params.voice_id = props.form.tts_voice
      }
    } else if (props.form.tts_inference_mode === 'comfyui') {
      // ComfyUI: 传 TTS 工作流 + voice_id + 参考音频(可选)
      if (props.form.tts_workflow) {
        params.workflow = props.form.tts_workflow
      }
      params.voice_id = props.form.tts_voice
      if (props.form.ref_audio) {
        params.ref_audio = props.form.ref_audio
      }
    }
    
    const res: any = await request('/api/tts/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    if (res.audio_path) {
      // 如果返回的是 HTTP URL（远程文件），直接使用；否则通过 filePreviewUrl 转本地路径
      if (res.audio_path.startsWith('http://') || res.audio_path.startsWith('https://')) {
        previewAudioUrl.value = res.audio_path
      } else {
        previewAudioUrl.value = filePreviewUrl(res.audio_path)
      }
    }
    ElMessage.success('预览语音生成成功')
  } catch (e: any) {
    ElMessage.error(`生成失败：${e.message}`)
  } finally {
    previewLoading.value = false
  }
}

async function handleAsrTranscribe() {
  if (!props.form.ref_audio) return
  asrLoading.value = true
  try {
    const res: any = await request('/api/audio/asr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio_path: props.form.ref_audio }),
    })
    props.form.voxcpm_prompt_text = res.text || ''
    ElMessage.success('语音转文字完成')
  } catch (e: any) {
    ElMessage.error(`转写失败：${e.message}`)
  } finally {
    asrLoading.value = false
  }
}

// ---- AI 一键改写 ----
const rewriteLoading = ref(false)

async function handleRewrite() {
  const text = props.form.goods_text?.trim()
  if (!text) {
    ElMessage.warning('请输入要改写的文案')
    return
  }
  rewriteLoading.value = true
  try {
    const prompt = `请改写以下口播文案，保持原意不变，使表达更流畅自然、更有吸引力，直接返回改写后的文案，不要多余的解释：\n\n${text}`
    const res: any = await request('/api/llm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, temperature: 0.7, max_tokens: 1024 }),
    })
    if (res.content) {
      props.form.goods_text = res.content.trim().slice(0, textMaxLength.value)
      ElMessage.success('改写完成')
    } else {
      ElMessage.warning('改写失败，请重试')
    }
  } catch (e: any) {
    ElMessage.error(`改写失败：${e.message}`)
  } finally {
    rewriteLoading.value = false
  }
}

// ---- 剪贴板粘贴 ----
async function handlePasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText()
    if (text) {
      mediaShareText.value = text
      ElMessage.success('已粘贴剪贴板内容')
      return
    }
  } catch {
    // Clipboard API 不可用（非 HTTPS/非 localhost 环境）
  }
  // 聚焦输入框，提示用户按 Ctrl+V 粘贴
  ElMessage.info('请点击输入框后按 Ctrl+V 粘贴')
  nextTick(() => {
    const el = document.querySelector('.media-dialog textarea') as HTMLTextAreaElement
    el?.focus()
  })
}

// ---- 短视频导入口播文案 ----
const mediaDialogVisible = ref(false)
const mediaShareText = ref('')
const mediaLoading = ref(false)

async function handleMediaParse() {
  if (!mediaShareText.value.trim()) {
    ElMessage.warning('请输入短视频分享信息')
    return
  }
  mediaLoading.value = true
  try {
    const res: any = await request('/api/media/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ share_text: mediaShareText.value.trim() }),
    })
    if (res.success && res.text) {
      props.form.goods_text = res.text.slice(0, textMaxLength.value)
      mediaDialogVisible.value = false
      ElMessage.success('口播文案导入成功')
    } else {
      ElMessage.warning(res.message || '未能提取到有效口播文案')
    }
  } catch (e: any) {
    ElMessage.error(`导入失败：${e.message}`)
  } finally {
    mediaLoading.value = false
  }
}
</script>

<style scoped>
/* 短视频导入弹窗：PC 固定 480px，手机自适应 92% */
@media (max-width: 640px) {
  :deep(.media-dialog) {
    --el-dialog-width: 92%;
  }
  :deep(.media-dialog .el-dialog) {
    width: 92% !important;
    max-width: 92vw !important;
  }
}

/* VIP 标识：亮眼金色渐变 + 闪烁效果 */
.vip-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #fff;
  background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.6), 0 0 16px rgba(255, 165, 0, 0.3);
  animation: vipPulse 2s ease-in-out infinite;
  cursor: pointer;
  user-select: none;
}

@keyframes vipPulse {
  0%, 100% {
    box-shadow: 0 0 8px rgba(255, 215, 0, 0.6), 0 0 16px rgba(255, 165, 0, 0.3);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 12px rgba(255, 215, 0, 0.9), 0 0 24px rgba(255, 165, 0, 0.5);
    transform: scale(1.05);
  }
}
</style>