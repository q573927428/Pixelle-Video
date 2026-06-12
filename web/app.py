# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Pixelle-Video Web UI - Main Entry Point

This is the entry point for the Streamlit multi-page application.
Uses st.navigation to define pages and set the default page to Home.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

# Add project root to sys.path for module imports
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st
import streamlit.components.v1 as components

# Setup page config (must be first Streamlit command)
st.set_page_config(
    page_title="Pixelle-Video - AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _is_port_open(host: str = "127.0.0.1", port: int = 8000, timeout: float = 0.35) -> bool:
    """Check whether the modern FastAPI UI port is already serving."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _start_modern_ui_server(port: int = 8000) -> tuple[bool, str]:
    """Start FastAPI modern UI server in the background when launched from Streamlit."""
    if _is_port_open(port=port):
        return True, f"http://localhost:{port}/modern"

    if st.session_state.get("_modern_ui_process_started"):
        time.sleep(0.8)
        return _is_port_open(port=port), f"http://localhost:{port}/modern"

    cmd = [
        sys.executable,
        "api/app.py",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    kwargs = {
        "cwd": str(_project_root),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        subprocess.Popen(cmd, **kwargs)
        st.session_state["_modern_ui_process_started"] = True
        for _ in range(20):
            if _is_port_open(port=port):
                return True, f"http://localhost:{port}/modern"
            time.sleep(0.25)
        return False, f"http://localhost:{port}/modern"
    except Exception as exc:
        return False, f"Failed to start Modern UI: {exc}"


def _render_ui_launcher():
    """Render startup UI chooser for users who launch with `uv run streamlit run web/app.py`."""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 12% 8%, rgba(124, 58, 237, 0.24), transparent 34%),
                radial-gradient(circle at 88% 12%, rgba(6, 182, 212, 0.18), transparent 32%),
                linear-gradient(135deg, #07111f 0%, #0c1222 48%, #101827 100%);
        }
        .ui-launcher-hero {
            padding: 2.2rem 0 1rem;
        }
        .ui-launcher-title {
            font-size: 3rem;
            line-height: 1.05;
            font-weight: 900;
            letter-spacing: -0.05em;
            margin: 0;
            color: #f8fafc;
        }
        .ui-launcher-title span {
            background: linear-gradient(90deg, #fff, #a78bfa 48%, #67e8f9);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .ui-launcher-subtitle {
            color: #94a3b8;
            font-size: 1rem;
            line-height: 1.8;
            max-width: 780px;
            margin-top: 1rem;
        }
        .ui-card {
            min-height: 230px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
            padding: 1.45rem;
            background: rgba(15, 23, 42, 0.72);
            box-shadow: 0 24px 80px rgba(2, 6, 23, 0.28);
        }
        .ui-card h3 {
            color: #f8fafc;
            margin: 0.5rem 0;
            font-size: 1.3rem;
        }
        .ui-card p {
            color: #94a3b8;
            line-height: 1.7;
        }
        .ui-badge {
            display: inline-flex;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(124, 58, 237, 0.18);
            color: #ddd6fe;
            font-size: 0.78rem;
            font-weight: 700;
        }
        </style>
        <div class="ui-launcher-hero">
          <h1 class="ui-launcher-title">Pixelle-Video <span>UI Launcher</span></h1>
          <div class="ui-launcher-subtitle">
            你仍然可以使用原来的命令 <code>uv run streamlit run web/app.py</code> 启动项目。
            启动后可在这里选择原 Streamlit 全功能界面，或新的现代软件化界面。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    classic_col, modern_col = st.columns(2)

    with classic_col:
        st.markdown(
            """
            <div class="ui-card">
              <div class="ui-badge">Classic · Streamlit</div>
              <h3>完整工具链 UI</h3>
              <p>保留现有所有工具、页面、Pipeline 和历史记录能力。适合素材创作、数字人、图生视频、动作迁移等完整复杂流程。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("进入 Classic UI", type="primary", use_container_width=True):
            st.session_state["ui_mode"] = "classic"
            st.rerun()

    with modern_col:
        st.markdown(
            """
            <div class="ui-card">
              <div class="ui-badge">Modern · FastAPI + Vue 3</div>
              <h3>现代软件工作台</h3>
              <p>新前端，卡片化布局、任务中心、资源管理、上传中心和核心视频生成。由当前 Streamlit 启动器自动拉起 FastAPI 服务。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("进入 Modern UI", type="primary", use_container_width=True):
            st.session_state["ui_mode"] = "modern"
            st.rerun()


def _render_modern_ui_embed():
    """Start and embed Modern UI while keeping the user's Streamlit startup command."""
    ok, modern_url = _start_modern_ui_server()

    top_col, action_col = st.columns([1, 0.24])
    with top_col:
        st.title("Pixelle Studio Modern UI")
        st.caption("由 Streamlit 启动器自动启动 FastAPI，并嵌入新的现代前端。")
    with action_col:
        if st.button("返回选择", use_container_width=True):
            st.session_state.pop("ui_mode", None)
            st.rerun()

    if not ok:
        st.warning(f"Modern UI 服务暂未就绪：{modern_url}")
        st.info("也可以手动运行：`uv run python api/app.py --host 0.0.0.0 --port 8000`")
        if st.button("重试启动 Modern UI", type="primary"):
            st.session_state.pop("_modern_ui_process_started", None)
            st.rerun()
        return

    st.success(f"Modern UI 已启动：{modern_url}")
    st.link_button("在新窗口打开 Modern UI", modern_url, use_container_width=True)

    try:
        urlopen(f"{modern_url.replace('/modern', '')}/health", timeout=1.0).read()
    except Exception:
        pass

    components.iframe(modern_url, height=920, scrolling=True)


def _run_classic_ui():
    """Run the original Streamlit multi-page application."""
    # Define pages using st.Page
    home_page = st.Page(
        "pages/1_🎬_Home.py",
        title="Home",
        icon="🎬",
        default=True
    )

    history_page = st.Page(
        "pages/2_📚_History.py",
        title="History",
        icon="📚"
    )

    # Set up navigation and run
    pg = st.navigation([home_page, history_page])
    pg.run()


def main():
    """Main entry point with UI mode selection."""
    ui_mode = st.session_state.get("ui_mode")

    if ui_mode == "classic":
        _run_classic_ui()
        return

    if ui_mode == "modern":
        _render_modern_ui_embed()
        return

    _render_ui_launcher()


if __name__ == "__main__":
    main()
