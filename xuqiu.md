# 终端1: 启动 FastAPI 后端
uv run python api/app.py --host 0.0.0.0 --port 8000

# 终端2: 启动 Vite 开发服务器（热加载）
cd modern_ui; pnpm run dev

# 访问: http://localhost:5173/modern/
# API 请求会自动代理到 :8000，修改代码自动热更新

uv run streamlit run web/app.py


第一次日淘选亚马逊还是乐天，选错真的会踩大坑。首先选日亚，为啥新手？

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


从历史上传选择里面添加删除功能






2026-06-12 20:37:34.858 | DEBUG    | pixelle_video.services.voxcpm_api:generate:314 -   Segment 1 audio at: C:\Users\Administrator\AppData\Local\Temp\gradio\87858b50f335d4dadd12055d6b51d2278da0c48a93d33a727085981f7dc00ca2\tmp1wm8i2yf.mp3
2026-06-12 20:37:34.859 | INFO     | pixelle_video.services.voxcpm_api:generate:340 - ✅ Generated audio: F:\qukuailian\ai\shipin\Pixelle-Video
\output\20260612_203706_a9f0\narration.mp3
2026-06-12 20:37:34.859 | INFO     | pixelle_video.services.tts_service:_call_voxcpm_tts:293 - ✅ Generated audio (VoxCPM API): F:\qukuailian\a
i\shipin\Pixelle-Video\output\20260612_203706_a9f0\narration.mp3
2026-06-12 20:37:34- pixelle_video.services.api_services.video_kling - WARNING - video_kling.py:93 - __init__ - KlingVideoClient: KLING_ACCESS_KEY / KLING_SECRET_KEY 未设置，请检查配置
2026-06-12 20:37:34.918 | INFO     | pixelle_video.services.api_media:_generate_video:552 - Generating video via API provider=dashscope, model=wan2.7-r2v
2026-06-12 20:37:34- pixelle_video.services.api_services.video_client - INFO - video_client.py:226 - _generate_wan - VideoClient: 路由至万象 model=wan2.7-r2v
INFO:     127.0.0.1:54130 - "GET /api/tasks/345bfb1d-db04-4805-b1fe-8fa0b76f47ab HTTP/1.1" 200 OK
2026-06-12 20:37:34- pixelle_video.services.api_services.video_dashscope - WARNING - video_dashscope.py:158 - _truncate_audio_to_duration - DashscopeVideoClient: 驱动音频时长 9.79s 超过最大允许时长 5s，将裁剪至 5s
2026-06-12 20:37:35- pixelle_video.services.api_services.video_dashscope - INFO - video_dashscope.py:177 - _truncate_audio_to_duration - DashscopeVideoClient: 音频已裁剪: F:\qukuailian\ai\shipin\Pixelle-Video\output\20260612_203706_a9f0\narration_truncated.mp3
2026-06-12 20:37:35- pixelle_video.services.api_services.video_dashscope - INFO - video_dashscope.py:261 - generate_video - DashscopeVideoClient: model=wan2.7-r2v, prompt=参考图1中的人物面对镜头自然口播。结合参考图2中的商品，生成竖屏商业口播视频。 口播文案：宝子们别瞧它名叫普通，用起
来可...
2026-06-12 20:37:36- dashscope - INFO - base_api.py:794 - wait - The task ebe89cdf-7847-4bf6-90a6-f7024d51439a is  RUNNING
2026-06-12 20:37:37- dashscope - INFO - base_api.py:794 - wait - The task ebe89cdf-7847-4bf6-90a6-f7024d51439a is  RUNNING

我前端视频时长设置的是8秒，为什么日志我看 最大允许时长是5秒？


modern_ui\src\views\TaskHistoryView.vue
历史记录添加删除功能