# 终端1: 启动 FastAPI 后端
uv run python api/app.py --host 0.0.0.0 --port 8000

# 终端2: 启动 Vite 开发服务器（热加载）
cd modern_ui
pnpm run dev
# 访问: http://localhost:5173/modern/
# API 请求会自动代理到 :8000，修改代码自动热更新