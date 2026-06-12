const { createApp } = Vue;

    const componentTemplates = {
      uploadBox: `
        <div class="upload-box-row">
          <el-upload class="compact-upload" drag multiple :auto-upload="false" :show-file-list="false" :on-change="file => $emit('upload', file.raw, category)">
            <div class="compact-upload-content">
              <span class="compact-upload-icon">＋</span>
              <span>上传文件</span>
              <span class="compact-upload-hint">点击或拖拽</span>
            </div>
          </el-upload>
          <el-button size="small" class="history-btn" @click="$emit('select-history', category)">
            <span style="margin-right:4px;">📂</span> 从历史选择
          </el-button>
        </div>
      `,
      uploadList: `
        <div class="upload-list">
          <div v-for="item in uploads" :key="item.path" class="upload-item">
            <span>{{ item.filename }} · {{ item.category }}</span>
            <el-button size="small" @click="window.open(item.url, '_blank')">预览</el-button>
          </div>
        </div>
      `,
      resourceCard: `
        <div class="card">
          <div class="card-header"><h3 class="card-title">{{ title }}</h3></div>
          <div class="card-body">
            <div v-if="!items.length" class="empty-preview">暂无资源</div>
            <div v-for="item in items" :key="item.key || item.path || item.name" class="upload-item">
              <span>{{ item[labelKey] || item[fallbackLabelKey] || item.key || item.name }}</span>
              <el-tag>{{ item[tagKey] || '-' }}</el-tag>
            </div>
          </div>
        </div>
      `,
      quickCreate: `
        <el-form label-position="top">
          <el-form-item label="创作模式">
            <el-radio-group v-model="form.mode">
              <el-radio-button value="generate" label="generate">AI 生成分镜</el-radio-button>
              <el-radio-button value="fixed" label="fixed">固定文案</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-alert
            v-if="form.mode === 'generate'"
            title="AI 生成分镜：输入主题/素材方向，由 AI 自动拆分场景、旁白和画面提示词。"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 14px;"
          />
          <el-alert
            v-else
            title="固定文案：直接使用输入内容作为旁白脚本，不再按主题重新扩写。"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom: 14px;"
          />

          <el-form-item label="视频标题"><el-input v-model="form.title" placeholder="可留空，由 AI 自动生成" clearable /></el-form-item>
          <el-form-item :label="form.mode === 'generate' ? '主题 / 创作方向' : '固定旁白文案'">
            <el-input
              v-model="form.text"
              type="textarea"
              :rows="form.mode === 'generate' ? 8 : 12"
              :placeholder="form.mode === 'generate' ? '输入视频主题、卖点、风格或营销方向...' : '输入完整旁白文案，每段可换行；系统会尽量按原文生成视频...'"
            />
          </el-form-item>
          <div class="soft-panel">
            <el-form-item v-if="form.mode === 'generate'" label="分镜数量"><el-slider v-model="form.n_scenes" :min="1" :max="20" show-input /></el-form-item>
            <div v-else class="small muted" style="margin-bottom: 14px;">固定文案模式会忽略分镜数量，按输入文案组织画面。</div>
            <el-form-item label="视频帧率"><el-slider v-model="form.video_fps" :min="15" :max="60" :step="5" show-input /></el-form-item>
          </div>
          <el-form-item label="画面模板">
            <el-select v-model="form.frame_template" filterable placeholder="选择 HTML 模板" style="width:100%;">
              <el-option v-for="tpl in templates" :key="tpl.key" :label="\`\${tpl.display_name} · \${tpl.size}\`" :value="tpl.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="媒体工作流">
            <el-select v-model="form.media_workflow" filterable clearable placeholder="默认/选择图片或视频工作流" style="width:100%;">
              <el-option v-for="wf in mediaWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="TTS 模式">
            <el-radio-group v-model="form.tts_inference_mode">
              <el-radio-button value="local">本地</el-radio-button>
              <el-radio-button value="comfyui">ComfyUI</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <div v-if="form.tts_inference_mode === 'local'" class="soft-panel">
            <el-form-item label="本地 TTS 引擎">
              <el-select v-model="form.tts_engine" clearable placeholder="选择本地 TTS 引擎" style="width:100%;">
                <el-option label="Edge TTS（本地默认）" value="edge_tts" />
                <el-option label="VoxCPM API（在线）" value="voxcpm_api" />
              </el-select>
            </el-form-item>
            <div v-if="form.tts_engine === 'voxcpm_api'" class="soft-panel">
              <el-form-item label="VoxCPM CFG"><el-slider v-model="form.voxcpm_cfg" :min="0.5" :max="5" :step="0.1" show-input /></el-form-item>
              <el-form-item label="VoxCPM 控制指令"><el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔、带一点营销感" /></el-form-item>
              <el-form-item label="VoxCPM Prompt Text"><el-input v-model="form.voxcpm_prompt_text" type="textarea" :rows="3" placeholder="可选：极致克隆模式参考文本" /></el-form-item>
              <el-checkbox v-model="form.voxcpm_use_prompt_text">启用 Prompt Text</el-checkbox>
              <el-checkbox v-model="form.voxcpm_normalize">Normalize</el-checkbox>
              <el-checkbox v-model="form.voxcpm_denoise">Denoise</el-checkbox>
            </div>
          </div>
          <el-form-item v-if="form.tts_inference_mode === 'comfyui'" label="TTS 工作流">
            <el-select v-model="form.tts_workflow" filterable clearable placeholder="默认/选择 TTS 工作流" style="width:100%;">
              <el-option v-for="wf in ttsWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.tts_inference_mode === 'comfyui' || (form.tts_inference_mode === 'local' && form.tts_engine === 'voxcpm_api')" label="参考音频（可选）"><upload-box category="ref_audio" @upload="(file, cat) => $emit('upload', file, cat, 'quick_ref_audio')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item label="图片风格前缀"><el-input v-model="form.prompt_prefix" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="背景音乐">
            <el-select v-model="form.bgm_path" clearable filterable placeholder="不使用 BGM" style="width:100%;">
              <el-option v-for="item in bgmFiles" :key="item.path" :label="item.name" :value="item.path" />
            </el-select>
          </el-form-item>
          <el-form-item label="BGM 音量"><el-slider v-model="form.bgm_volume" :min="0" :max="1" :step="0.05" /></el-form-item>
        </el-form>
      `,
      assetBased: `
        <el-form label-position="top">
          <el-alert title="完整素材创作已接入现代 UI" type="success" :closable="false" show-icon style="margin-bottom:14px;" />
          <el-form-item label="图片/视频素材"><upload-box category="image" @upload="(file, cat) => $emit('upload', file, cat, 'asset')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item label="视频标题"><el-input v-model="form.video_title" placeholder="例如：宠物店年终促销" /></el-form-item>
          <el-form-item label="创作意图"><el-input v-model="form.intent" type="textarea" :rows="5" placeholder="描述你想表达的卖点、风格、受众..." /></el-form-item>
          <div class="soft-panel">
            <el-form-item label="目标时长（秒）"><el-slider v-model="form.duration" :min="15" :max="120" :step="5" show-input /></el-form-item>
            <el-form-item label="素材分析来源">
              <el-radio-group v-model="form.source">
                <el-radio-button label="runninghub">RunningHub</el-radio-button>
                <el-radio-button label="selfhost">本地 ComfyUI</el-radio-button>
                <el-radio-button label="api">API VLM</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </div>
          <el-form-item label="分析图片工作流"><el-input v-model="form.analysis_image_workflow" placeholder="如 runninghub/analyse_image.json，可留空默认" /></el-form-item>
          <el-form-item label="分析视频工作流"><el-input v-model="form.analysis_video_workflow" placeholder="如 runninghub/analyse_video.json，可留空默认" /></el-form-item>
          <el-form-item label="API VLM 模型"><el-input v-model="form.analysis_vlm_model" placeholder="选择 API 来源时可填写模型 key" /></el-form-item>
          <el-form-item label="API 素材动画工作流"><el-input v-model="form.api_video_workflow" placeholder="可选，api/..." /></el-form-item>
          <el-form-item label="TTS 声音"><el-input v-model="form.voice_id" /></el-form-item>
          <el-form-item label="TTS 语速"><el-slider v-model="form.tts_speed" :min="0.5" :max="2" :step="0.1" /></el-form-item>
          <el-form-item label="背景音乐">
            <el-select v-model="form.bgm_path" clearable filterable placeholder="不使用 BGM" style="width:100%;">
              <el-option v-for="item in bgmFiles" :key="item.path" :label="item.name" :value="item.path" />
            </el-select>
          </el-form-item>
          <upload-list :uploads="form.assets.map(path => ({ path, filename: path.split(/[\\\\/]/).pop(), category: 'asset' }))"></upload-list>
        </el-form>
      `,
      digitalHuman: `
        <el-form label-position="top">
          <el-alert title="数字人口播完整生成链路已接入现代 UI" type="success" :closable="false" show-icon style="margin-bottom:14px;" />
          <el-form-item label="模式">
            <el-radio-group v-model="form.mode">
              <el-radio-button label="digital">商品口播</el-radio-button>
              <el-radio-button label="customize">自定义口播</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="角色图片"><upload-box category="character_image" @upload="(file, cat) => $emit('upload', file, cat, 'digital_character')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item v-if="form.mode === 'digital'" label="商品图片"><upload-box category="goods_image" @upload="(file, cat) => $emit('upload', file, cat, 'digital_goods')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item v-if="form.mode === 'digital'" label="商品标题"><el-input v-model="form.goods_title" placeholder="例如：智能保温杯" /></el-form-item>
          <el-form-item label="口播文案"><el-input v-model="form.goods_text" type="textarea" :rows="6" placeholder="可填写固定口播文案；商品口播模式下留空可自动生成" /></el-form-item>
          <div class="soft-panel">
            <el-form-item label="前置图片工作流"><el-input v-model="form.workflow_config.first_workflow_path" /></el-form-item>
            <el-form-item label="商品合成图片工作流"><el-input v-model="form.workflow_config.third_workflow_path" /></el-form-item>
            <el-form-item label="口播视频合成工作流"><el-input v-model="form.workflow_config.second_workflow_path" /></el-form-item>
            <el-form-item label="API 图片工作流"><el-input v-model="form.workflow_config.api_image_workflow" placeholder="可选 api/..." /></el-form-item>
            <el-form-item label="API 口播视频工作流"><el-input v-model="form.workflow_config.api_video_workflow" placeholder="可选 api/..." /></el-form-item>
          </div>
          <el-form-item label="TTS 模式">
            <el-radio-group v-model="form.tts_inference_mode">
              <el-radio-button label="local">本地</el-radio-button>
              <el-radio-button label="comfyui">ComfyUI</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.tts_inference_mode === 'local'" label="本地 TTS 引擎">
            <el-select v-model="form.tts_engine" clearable placeholder="选择本地 TTS 引擎" style="width:100%;">
              <el-option label="Edge TTS（本地默认）" value="edge_tts" />
              <el-option label="VoxCPM API（在线）" value="voxcpm_api" />
            </el-select>
          </el-form-item>
          <div v-if="form.tts_inference_mode === 'local' && form.tts_engine === 'voxcpm_api'" class="soft-panel">
            <el-form-item label="VoxCPM CFG"><el-slider v-model="form.voxcpm_cfg" :min="0.5" :max="5" :step="0.1" show-input /></el-form-item>
            <el-form-item label="VoxCPM 控制指令"><el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔、带一点营销感" /></el-form-item>
            <el-form-item label="VoxCPM Prompt Text"><el-input v-model="form.voxcpm_prompt_text" type="textarea" :rows="3" placeholder="可选：极致克隆模式参考文本" /></el-form-item>
            <el-checkbox v-model="form.voxcpm_use_prompt_text">启用 Prompt Text</el-checkbox>
            <el-checkbox v-model="form.voxcpm_normalize">Normalize</el-checkbox>
            <el-checkbox v-model="form.voxcpm_denoise">Denoise</el-checkbox>
          </div>
          <el-form-item label="TTS 声音"><el-input v-model="form.tts_voice" /></el-form-item>
          <el-form-item label="TTS 语速"><el-slider v-model="form.tts_speed" :min="0.5" :max="2" :step="0.1" /></el-form-item>
          <el-form-item label="TTS 工作流"><el-select v-model="form.tts_workflow" filterable clearable placeholder="ComfyUI TTS 工作流" style="width:100%;"><el-option v-for="wf in ttsWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" /></el-select></el-form-item>
          <el-form-item label="参考音频"><upload-box category="ref_audio" @upload="(file, cat) => $emit('upload', file, cat, 'digital_ref_audio')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <upload-list :uploads="[...form.character_assets, ...form.goods_assets].map(path => ({ path, filename: path.split(/[\\\\/]/).pop(), category: 'digital' }))"></upload-list>
        </el-form>
      `,
      i2v: `
        <el-form label-position="top">
          <el-alert title="图生视频完整生成链路已接入现代 UI" type="success" :closable="false" show-icon style="margin-bottom:14px;" />
          <el-form-item label="首帧图片"><upload-box category="image" @upload="(file, cat) => $emit('upload', file, cat, 'i2v_image')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item label="提示词"><el-input v-model="form.prompt_text" type="textarea" :rows="7" placeholder="描述画面如何运动、镜头、风格..." /></el-form-item>
          <el-form-item label="图生视频工作流">
            <el-select v-model="form.workflow_key" filterable allow-create placeholder="选择或手动输入 i2v_ / api 工作流" style="width:100%;">
              <el-option v-for="wf in workflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="API 参数 JSON（可选）"><el-input v-model="form.api_video_params_json" type="textarea" :rows="4" placeholder='{"duration":5,"video_ratio":"9:16"}' /></el-form-item>
          <upload-list :uploads="form.image_assets.map(path => ({ path, filename: path.split(/[\\\\/]/).pop(), category: 'i2v' }))"></upload-list>
        </el-form>
      `,
      actionTransfer: `
        <el-form label-position="top">
          <el-alert title="动作迁移完整生成链路已接入现代 UI" type="success" :closable="false" show-icon style="margin-bottom:14px;" />
          <el-form-item label="参考动作视频"><upload-box category="video" @upload="(file, cat) => $emit('upload', file, cat, 'action_video')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item label="目标人物/图片"><upload-box category="image" @upload="(file, cat) => $emit('upload', file, cat, 'action_image')" @select-history="(cat) => $emit('select-history', cat)"></upload-box></el-form-item>
          <el-form-item label="提示词"><el-input v-model="form.prompt_text" type="textarea" :rows="6" placeholder="描述迁移后的画面风格..." /></el-form-item>
          <el-form-item label="时长（秒）"><el-slider v-model="form.duration" :min="1" :max="30" show-input /></el-form-item>
          <el-form-item label="动作迁移工作流">
            <el-select v-model="form.workflow_key" filterable allow-create placeholder="选择或手动输入 af_ / api 工作流" style="width:100%;">
              <el-option v-for="wf in workflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="API 参数 JSON（可选）"><el-input v-model="form.api_video_params_json" type="textarea" :rows="4" placeholder='{"duration":5}' /></el-form-item>
          <upload-list :uploads="[...form.video_assets, ...form.image_assets].map(path => ({ path, filename: path.split(/[\\\\/]/).pop(), category: 'action_transfer' }))"></upload-list>
        </el-form>
      `,
    };

    const UploadBox = { props: ["category"], emits: ["upload", "select-history"], template: componentTemplates.uploadBox };
    const UploadList = { props: ["uploads"], template: componentTemplates.uploadList };
    const ResourceCard = { props: ["title", "items", "labelKey", "fallbackLabelKey", "tagKey"], template: componentTemplates.resourceCard };
    const QuickCreateForm = { components: { UploadBox }, props: ["form", "templates", "mediaWorkflows", "ttsWorkflows", "bgmFiles"], emits: ["upload", "select-history"], template: componentTemplates.quickCreate };
    const AssetBasedForm = { components: { UploadBox, UploadList }, props: ["form", "uploads", "bgmFiles"], emits: ["upload", "select-history"], template: componentTemplates.assetBased };
    const DigitalHumanForm = { components: { UploadBox, UploadList }, props: ["form", "uploads", "mediaWorkflows", "ttsWorkflows"], emits: ["upload", "select-history"], template: componentTemplates.digitalHuman };
    const I2vForm = { components: { UploadBox, UploadList }, props: ["form", "uploads", "workflows"], emits: ["upload", "select-history"], template: componentTemplates.i2v };
    const ActionTransferForm = { components: { UploadBox, UploadList }, props: ["form", "uploads", "workflows"], emits: ["upload", "select-history"], template: componentTemplates.actionTransfer };

    createApp({
      components: {
        UploadBox,
        UploadList,
        ResourceCard,
        QuickCreateForm,
        AssetBasedForm,
        DigitalHumanForm,
        I2vForm,
        ActionTransferForm,
      },
      data() {
        return {
          activeView: "studio",
          selectedTool: "quick_create",
          uploadCategory: "image",
          health: { ok: false },
          running: false,
          progress: 0,
          statusText: "等待开始",
          pollTimer: null,
          templates: [],
          mediaWorkflows: [],
          ttsWorkflows: [],
          ttsVoices: [],
          bgmFiles: [],
          tasks: [],
          uploads: [],
          result: {},
          tools: [
            { key: "quick_create", icon: "⚡", name: "快速创作", badge: "Standard", desc: "文本到视频，AI 分镜/固定文案" },
            { key: "custom_media", icon: "🎨", name: "素材创作", badge: "Asset", desc: "上传图片/视频素材生成成片" },
            { key: "digital_human", icon: "🤖", name: "数字人", badge: "Digital", desc: "角色图 + 商品图 + 口播合成" },
            { key: "image_to_video", icon: "🎥", name: "图生视频", badge: "I2V", desc: "首帧图片驱动视频生成" },
            { key: "action_transfer", icon: "💃", name: "动作迁移", badge: "Action", desc: "参考视频动作迁移到目标图片" },
          ],
          navItems: [
            { key: "studio", icon: "✨", label: "创作台" },
            { key: "assets", icon: "📤", label: "上传中心" },
            { key: "tasks", icon: "📊", label: "任务中心" },
            { key: "resources", icon: "🧩", label: "资源管理" },
          ],
          quickForm: {
            text: "",
            mode: "generate",
            title: "",
            n_scenes: 5,
            min_narration_words: 5,
            max_narration_words: 20,
            min_image_prompt_words: 30,
            max_image_prompt_words: 60,
            tts_inference_mode: "local",
            tts_engine: "",
            tts_workflow: null,
            ref_audio: null,
            media_workflow: null,
            video_fps: 30,
            frame_template: null,
            prompt_prefix: "",
            bgm_path: null,
            bgm_volume: 0.3,
            tts_speed: 1.2,
            voxcpm_cfg: 2.0,
            voxcpm_normalize: false,
            voxcpm_denoise: false,
            voxcpm_control_instruction: "",
            voxcpm_use_prompt_text: false,
            voxcpm_prompt_text: "",
          },
          assetForm: {
            assets: [],
            video_title: "",
            intent: "",
            duration: 30,
            source: "runninghub",
            analysis_image_workflow: "runninghub/analyse_image.json",
            analysis_video_workflow: "runninghub/analyse_video.json",
            analysis_vlm_model: "",
            api_video_workflow: "",
            api_video_params: {},
            voice_id: "zh-CN-YunjianNeural",
            tts_speed: 1.2,
            bgm_path: null,
            bgm_volume: 0.2,
            bgm_mode: "loop",
          },
          digitalForm: {
            mode: "digital",
            character_assets: [],
            goods_assets: [],
            goods_title: "",
            goods_text: "",
            workflow_config: {
              first_workflow_path: "workflows/runninghub/digital_image.json",
              second_workflow_path: "workflows/runninghub/digital_combination.json",
              third_workflow_path: "workflows/runninghub/digital_customize.json",
              api_image_workflow: "",
              api_video_workflow: "",
              api_video_params: {},
            },
            tts_inference_mode: "local",
            tts_engine: "",
            tts_voice: "zh-CN-YunjianNeural",
            tts_speed: 1.2,
            tts_workflow: "",
            ref_audio: "",
            voxcpm_cfg: 2.0,
            voxcpm_normalize: false,
            voxcpm_denoise: false,
            voxcpm_control_instruction: "",
            voxcpm_use_prompt_text: false,
            voxcpm_prompt_text: "",
          },
          i2vForm: {
            image_assets: [],
            prompt_text: "",
            workflow_key: "",
            api_video_params_json: "",
          },
          actionForm: {
            video_assets: [],
            image_assets: [],
            prompt_text: "",
            duration: 5,
            workflow_key: "",
            api_video_params_json: "",
          },
          historyDialog: {
            visible: false,
            loading: false,
            records: [],
            pendingCategory: "",
            pendingTarget: "",
          },
        };
      },
      computed: {
        currentTool() {
          return this.tools.find(item => item.key === this.selectedTool) || this.tools[0];
        },
        progressStatus() {
          if (this.progress >= 100) return "success";
          if (this.statusText.includes("失败")) return "exception";
          return undefined;
        },
        i2vWorkflows() {
          return this.mediaWorkflows.filter(wf => {
            const key = (wf.key || wf.path || "").toLowerCase();
            const name = (wf.name || key).toLowerCase();
            return key.startsWith("api/") || name.startsWith("i2v_") || key.includes("/i2v_");
          });
        },
        actionWorkflows() {
          return this.mediaWorkflows.filter(wf => {
            const key = (wf.key || wf.path || "").toLowerCase();
            const name = (wf.name || key).toLowerCase();
            return key.startsWith("api/") || name.startsWith("af_") || key.includes("/af_");
          });
        },
      },
      mounted() {
        this.loadAll();
      },
      methods: {
        async request(url, options = {}) {
          const response = await fetch(url, options);
          if (!response.ok) {
            let detail = response.statusText;
            try {
              const data = await response.json();
              detail = data.detail || data.message || JSON.stringify(data);
            } catch (_) {}
            throw new Error(detail);
          }
          return response.json();
        },
        async loadAll() {
          await Promise.allSettled([this.checkHealth(), this.loadResources(), this.loadTasks()]);
        },
        async checkHealth() {
          try {
            await this.request("/health");
            this.health.ok = true;
          } catch (_) {
            this.health.ok = false;
          }
        },
        async loadResources() {
          try {
            const [templates, media, tts, bgm, voices] = await Promise.all([
              this.request("/api/resources/templates"),
              this.request("/api/resources/workflows/media"),
              this.request("/api/resources/workflows/tts"),
              this.request("/api/resources/bgm"),
              this.request("/api/resources/tts-voices"),
            ]);
            this.templates = templates.templates || [];
            this.mediaWorkflows = media.workflows || [];
            this.ttsWorkflows = tts.workflows || [];
            this.bgmFiles = bgm.bgm_files || [];
            this.ttsVoices = voices.voices || [];

            if (!this.quickForm.frame_template && this.templates.length) {
              const portrait = this.templates.find(tpl => tpl.orientation === "portrait");
              this.quickForm.frame_template = (portrait || this.templates[0]).key;
            }
            if (!this.i2vForm.workflow_key && this.i2vWorkflows.length) {
              this.i2vForm.workflow_key = this.i2vWorkflows[0].key;
            }
            if (!this.actionForm.workflow_key && this.actionWorkflows.length) {
              this.actionForm.workflow_key = this.actionWorkflows[0].key;
            }
          } catch (error) {
            ElementPlus.ElMessage.error(`资源加载失败：${error.message}`);
          }
        },
        async loadTasks() {
          try {
            this.tasks = await this.request("/api/tasks?limit=30");
          } catch (_) {
            this.tasks = [];
          }
        },
        parseJson(text) {
          if (!text || !text.trim()) return {};
          try {
            return JSON.parse(text);
          } catch (error) {
            throw new Error(`JSON 参数格式错误：${error.message}`);
          }
        },
        cleanedPayload(payload) {
          return Object.fromEntries(
            Object.entries(payload).filter(([_, value]) => value !== "" && value !== null && value !== undefined)
          );
        },
        async generateCurrent() {
          const handlers = {
            quick_create: this.generateQuickCreate,
            custom_media: this.generateAssetBased,
            digital_human: this.generateDigitalHuman,
            image_to_video: this.generateI2v,
            action_transfer: this.generateActionTransfer,
          };
          await handlers[this.selectedTool]();
        },
        async submitTask(url, payload) {
          this.running = true;
          this.progress = 2;
          this.statusText = "任务提交中...";
          this.result = {};

          try {
            const data = await this.request(url, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            this.statusText = `任务已创建：${data.task_id}`;
            this.progress = 8;
            this.pollTask(data.task_id);
          } catch (error) {
            this.running = false;
            this.statusText = `提交失败：${error.message}`;
            ElementPlus.ElMessage.error(this.statusText);
          }
        },
        async generateQuickCreate() {
          if (!this.quickForm.text.trim()) return ElementPlus.ElMessage.warning("请输入主题或文案");
          if (!this.quickForm.frame_template) return ElementPlus.ElMessage.warning("请选择画面模板");
          await this.submitTask("/api/video/generate/async", this.cleanedPayload(this.quickForm));
        },
        async generateAssetBased() {
          if (!this.assetForm.assets.length) return ElementPlus.ElMessage.warning("请上传素材图片或视频");
          await this.submitTask("/api/pipelines/asset-based/async", this.cleanedPayload(this.assetForm));
        },
        async generateDigitalHuman() {
          if (!this.digitalForm.character_assets.length) return ElementPlus.ElMessage.warning("请上传角色图片");
          if (this.digitalForm.mode === "digital" && !this.digitalForm.goods_assets.length) return ElementPlus.ElMessage.warning("请上传商品图片");
          await this.submitTask("/api/pipelines/digital-human/async", this.cleanedPayload(this.digitalForm));
        },
        async generateI2v() {
          if (!this.i2vForm.image_assets.length) return ElementPlus.ElMessage.warning("请上传首帧图片");
          if (!this.i2vForm.prompt_text.trim()) return ElementPlus.ElMessage.warning("请输入提示词");
          if (!this.i2vForm.workflow_key) return ElementPlus.ElMessage.warning("请选择图生视频工作流");
          const payload = {
            image_assets: this.i2vForm.image_assets,
            prompt_text: this.i2vForm.prompt_text,
            workflow_key: this.i2vForm.workflow_key,
            api_video_params: this.parseJson(this.i2vForm.api_video_params_json),
          };
          await this.submitTask("/api/pipelines/image-to-video/async", payload);
        },
        async generateActionTransfer() {
          if (!this.actionForm.video_assets.length) return ElementPlus.ElMessage.warning("请上传参考动作视频");
          if (!this.actionForm.image_assets.length) return ElementPlus.ElMessage.warning("请上传目标图片");
          if (!this.actionForm.prompt_text.trim()) return ElementPlus.ElMessage.warning("请输入提示词");
          if (!this.actionForm.workflow_key) return ElementPlus.ElMessage.warning("请选择动作迁移工作流");
          const payload = {
            video_assets: this.actionForm.video_assets,
            image_assets: this.actionForm.image_assets,
            prompt_text: this.actionForm.prompt_text,
            duration: this.actionForm.duration,
            workflow_key: this.actionForm.workflow_key,
            api_video_params: this.parseJson(this.actionForm.api_video_params_json),
          };
          await this.submitTask("/api/pipelines/action-transfer/async", payload);
        },
        pollTask(taskId) {
          if (this.pollTimer) clearInterval(this.pollTimer);

          const tick = async () => {
            try {
              const task = await this.request(`/api/tasks/${taskId}`);
              this.progress = Math.max(8, Math.min(99, this.taskPercentage(task)));
              this.statusText = this.taskMessage(task);

              if (task.status === "completed") {
                this.running = false;
                this.progress = 100;
                this.result = task.result || {};
                this.statusText = "生成完成";
                clearInterval(this.pollTimer);
                await this.loadTasks();
                ElementPlus.ElMessage.success("视频生成完成");
              }

              if (["failed", "cancelled"].includes(task.status)) {
                this.running = false;
                this.statusText = `任务失败：${task.error || task.message || task.status}`;
                clearInterval(this.pollTimer);
                await this.loadTasks();
                ElementPlus.ElMessage.error(this.statusText);
              }
            } catch (error) {
              this.running = false;
              this.statusText = `任务查询失败：${error.message}`;
              clearInterval(this.pollTimer);
            }
          };

          tick();
          this.pollTimer = setInterval(tick, 3000);
        },
        taskPercentage(task) {
          const progress = task.progress;
          if (!progress) return task.status === "completed" ? 100 : 0;
          if (typeof progress === "number") return Math.round(progress * 100);
          if (typeof progress.percentage === "number") return Math.round(progress.percentage);
          if (typeof progress.current === "number" && typeof progress.total === "number" && progress.total > 0) {
            return Math.round(progress.current / progress.total * 100);
          }
          return 0;
        },
        taskMessage(task) {
          if (task.error) return task.error;
          if (task.progress && typeof task.progress === "object" && task.progress.message) return task.progress.message;
          return task.message || `状态：${task.status}`;
        },
        async uploadFile(rawFile, category, target) {
          if (!rawFile) return;

          const formData = new FormData();
          formData.append("file", rawFile);
          formData.append("category", category);

          try {
            const data = await this.request("/api/files/upload", { method: "POST", body: formData });
            this.uploads.unshift(data);
            this.applyUploadTarget(data.path, target, category);
            // Save to localStorage for persistence across page refreshes
            this._saveToLocalHistory(data, category);
            ElementPlus.ElMessage.success(`${data.filename} 上传成功`);
          } catch (error) {
            ElementPlus.ElMessage.error(`上传失败：${error.message}`);
          }
        },
        _saveToLocalHistory(data, category) {
          try {
            const key = "pixelle_upload_history";
            let history = JSON.parse(localStorage.getItem(key) || "[]");
            const record = {
              id: data.stored_name || Date.now().toString(),
              category: category || data.category || "misc",
              name: data.filename || "unknown",
              path: data.path,
              url: data.url || "",  // Save the API URL for preview
            };
            history.unshift(record);
            // Keep max 100 records
            if (history.length > 100) history = history.slice(0, 100);
            localStorage.setItem(key, JSON.stringify(history));
          } catch (_) {}
        },
        _loadLocalHistory() {
          try {
            const key = "pixelle_upload_history";
            return JSON.parse(localStorage.getItem(key) || "[]");
          } catch (_) {
            return [];
          }
        },
        applyUploadTarget(path, target, category) {
          if (target === "quick_ref_audio") this.quickForm.ref_audio = path;
          else if (target === "asset") this.assetForm.assets.push(path);
          else if (target === "digital_character") this.digitalForm.character_assets.push(path);
          else if (target === "digital_goods") this.digitalForm.goods_assets.push(path);
          else if (target === "digital_ref_audio") this.digitalForm.ref_audio = path;
          else if (target === "i2v_image") this.i2vForm.image_assets.push(path);
          else if (target === "action_video") this.actionForm.video_assets.push(path);
          else if (target === "action_image") this.actionForm.image_assets.push(path);
          else if (category === "image") this.assetForm.assets.push(path);
          else if (category === "video") this.actionForm.video_assets.push(path);
          else if (category === "ref_audio") {
            this.quickForm.ref_audio = path;
            this.digitalForm.ref_audio = path;
          }
        },
        async openHistoryDialog(category) {
          this.historyDialog.visible = true;
          this.historyDialog.loading = true;
          this.historyDialog.records = [];
          try {
            // Build records: localStorage (persists across refreshes) + session uploads
            const seenPaths = new Set();
            let records = [];

            // 1. Load from localStorage (persistent cross-session history)
            const localHistory = this._loadLocalHistory();
            for (const r of localHistory) {
              if (!seenPaths.has(r.path)) {
                // Ensure the record has a 'url' field for preview
                if (!r.url && r.path) {
                  const parts = r.path.replace(/\\/g, '/').split('/');
                  const uploadIdx = parts.indexOf('temp');
                  if (uploadIdx >= 0) {
                    r.url = '/api/files/' + parts.slice(uploadIdx).join('/');
                  }
                }
                records.push(r);
                seenPaths.add(r.path);
              }
            }

            // 2. Merge with current session uploads (most recent first)
            for (const u of this.uploads) {
              const path = u.path;
              if (!seenPaths.has(path)) {
                records.push({
                  id: u.stored_name || path,
                  category: u.category || "misc",
                  name: u.filename || path?.split(/[\\/]/).pop() || "unknown",
                  path: path,
                });
                seenPaths.add(path);
              }
            }

            // Show ALL records - user sees everything uploaded
            this.historyDialog.records = records.slice(0, 50);
            this.historyDialog.pendingCategory = category;
          } catch (error) {
            ElementPlus.ElMessage.error(`加载历史记录失败：${error.message}`);
          } finally {
            this.historyDialog.loading = false;
          }
        },
        selectHistoryRecord(record) {
          const category = record.category || this.historyDialog.pendingCategory;
          // Route based on category - ref_audio goes to both quick and digital forms
          if (category === "ref_audio") {
            this.quickForm.ref_audio = record.path;
            this.digitalForm.ref_audio = record.path;
          } else if (category === "character_image") {
            this.digitalForm.character_assets.push(record.path);
          } else if (category === "goods_image") {
            this.digitalForm.goods_assets.push(record.path);
          } else if (category === "video") {
            this.actionForm.video_assets.push(record.path);
          } else {
            // image or fallback: add to asset form, also to i2v/action image
            this.assetForm.assets.push(record.path);
            this.i2vForm.image_assets.push(record.path);
            this.actionForm.image_assets.push(record.path);
          }
          this.historyDialog.visible = false;
          ElementPlus.ElMessage.success(`已选择：${record.name}`);
        },
        isImageFile(filename) {
          return /\.(jpg|jpeg|png|gif|webp)$/i.test(filename);
        },
        isVideoFile(filename) {
          return /\.(mp4|mov|avi|mkv|webm)$/i.test(filename);
        },
        isAudioFile(filename) {
          return /\.(mp3|wav|flac|m4a|aac|ogg)$/i.test(filename);
        },
        makePreviewUrl(rec) {
          // Use saved url (relative_path from upload response), or fallback to filePreviewUrl on path
          if (rec.url) return rec.url;
          if (rec.relative_path) return `/api/files/${rec.relative_path}`;
          // Try to extract relative path from the absolute path
          const parts = (rec.path || '').replace(/\\\\/g, '/').replace(/\\/g, '/').split('/');
          const idx = parts.indexOf('temp');
          if (idx >= 0) return '/api/files/' + parts.slice(idx).join('/');
          return this.filePreviewUrl(rec.path);
        },
        showIconFallback(event) {
          // Replace the errored element with a simple icon span
          const el = event.target;
          if (el) {
            const parent = el.parentElement;
            if (parent) {
              parent.innerHTML = '<span style="font-size:28px;">' + this.getFileIcon(el.src ? el.src.split('/').pop() : '') + '</span>';
            }
          }
        },
        previewFile(rec) {
          const url = rec.url || this.makePreviewUrl(rec);
          if (url) {
            const a = document.createElement('a');
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener';
            a.click();
          }
        },
        getFileIcon(filename) {
          const ext = filename.split('.').pop().toLowerCase();
          if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return '🖼️';
          if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext)) return '🎬';
          if (['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg'].includes(ext)) return '🎵';
          return '📄';
        },
        currentAssetRows() {
          if (this.selectedTool === "quick_create") {
            return [this.quickForm.ref_audio].filter(Boolean);
          }
          if (this.selectedTool === "custom_media") {
            return this.assetForm.assets;
          }
          if (this.selectedTool === "digital_human") {
            return [
              ...this.digitalForm.character_assets,
              ...this.digitalForm.goods_assets,
              this.digitalForm.ref_audio,
            ].filter(Boolean);
          }
          if (this.selectedTool === "image_to_video") {
            return this.i2vForm.image_assets;
          }
          if (this.selectedTool === "action_transfer") {
            return [...this.actionForm.video_assets, ...this.actionForm.image_assets];
          }
          return [];
        },
        currentWorkflowRows() {
          if (this.selectedTool === "quick_create") {
            const ttsMode = this.quickForm.tts_inference_mode === "local"
              ? `本地${this.quickForm.tts_engine ? " (" + (this.quickForm.tts_engine === "voxcpm_api" ? "VoxCPM" : "Edge TTS") + ")" : ""}`
              : `ComfyUI${this.quickForm.tts_workflow ? " (" + this.quickForm.tts_workflow + ")" : ""}`;
            return [
              { label: "模板", value: this.quickForm.frame_template },
              { label: "媒体工作流", value: this.quickForm.media_workflow || "默认" },
              { label: "TTS 模式", value: ttsMode },
            ];
          }
          if (this.selectedTool === "custom_media") {
            return [
              { label: "素材分析来源", value: this.assetForm.source },
              { label: "分析图片", value: this.assetForm.analysis_image_workflow || "默认" },
              { label: "分析视频", value: this.assetForm.analysis_video_workflow || "默认" },
              { label: "素材动画", value: this.assetForm.api_video_workflow || "未启用" },
            ];
          }
          if (this.selectedTool === "digital_human") {
            return [
              { label: "TTS 模式", value: this.digitalForm.tts_inference_mode },
              { label: "TTS 引擎", value: this.digitalForm.tts_engine || "默认" },
              { label: "前置图片", value: this.digitalForm.workflow_config.api_image_workflow || this.digitalForm.workflow_config.first_workflow_path },
              { label: "口播视频", value: this.digitalForm.workflow_config.api_video_workflow || this.digitalForm.workflow_config.second_workflow_path },
            ];
          }
          if (this.selectedTool === "image_to_video") {
            return [{ label: "图生视频工作流", value: this.i2vForm.workflow_key }];
          }
          if (this.selectedTool === "action_transfer") {
            return [
              { label: "动作迁移工作流", value: this.actionForm.workflow_key },
              { label: "时长", value: `${this.actionForm.duration}s` },
            ];
          }
          return [];
        },
        filePreviewUrl(path) {
          if (!path) return "";
          const normalized = path.replaceAll("\\\\", "/");
          const outputIndex = normalized.indexOf("output/");
          const uploadIndex = normalized.indexOf("temp/uploads/");
          if (outputIndex >= 0) return `/api/files/${normalized.slice(outputIndex)}`;
          if (uploadIndex >= 0) return `/api/files/${normalized.slice(uploadIndex)}`;
          return `/api/files/${encodeURIComponent(normalized)}`;
        },
        downloadResult() {
          if (this.result.video_url) window.open(this.result.video_url, "_blank");
        },
        tagType(status) {
          return { completed: "success", running: "warning", pending: "info", failed: "danger", cancelled: "info" }[status] || "info";
        },
      },
    }).use(ElementPlus).mount("#app");