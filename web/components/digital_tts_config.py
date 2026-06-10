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
Style configuration components for web UI (middle column)
"""

import os
from pathlib import Path

import streamlit as st
from loguru import logger

from web.i18n import tr, get_language
from web.utils.async_helpers import run_async
from web.utils.upload_history import render_upload_area
from pixelle_video.config import config_manager


def render_style_config(pixelle_video):
    """Render style configuration section (middle column)"""
    # TTS Section (moved from left column)
    # ====================================================================
    with st.container(border=True):
        st.markdown(f"**{tr('section.tts')}**")
        
        with st.expander(tr("help.feature_description"), expanded=False):
            st.markdown(f"**{tr('help.what')}**")
            st.markdown(tr("tts.what"))
            st.markdown(f"**{tr('help.how')}**")
            st.markdown(tr("tts.how"))
        
        # Get TTS config
        comfyui_config = config_manager.get_comfyui_config()
        tts_config = comfyui_config["tts"]
        
        # Inference mode selection
        tts_mode = st.radio(
            tr("tts.inference_mode"),
            ["local", "comfyui"],
            horizontal=True,
            format_func=lambda x: tr(f"tts.mode.{x}"),
            index=0 if tts_config.get("inference_mode", "local") == "local" else 1,
            key="digital_tts_inference_mode"
        )
        
        # Show hint based on mode and engine
        if tts_mode == "local":
            st.caption(tr("tts.mode.local_hint"))
        else:
            st.caption(tr("tts.mode.comfyui_hint"))
        
        # ================================================================
        # Local Mode UI
        # ================================================================
        if tts_mode == "local":
            # Get saved config
            local_config = tts_config.get("local", {})
            saved_engine = local_config.get("engine", "edge_tts")
            
            # TTS Engine selector
            engine_options = ["edge_tts", "voxcpm_api"]
            engine_labels = {
                "edge_tts": tr("tts.engine.edge_tts"),
                "voxcpm_api": tr("tts.engine.voxcpm_api"),
            }
            engine_default_index = engine_options.index(saved_engine) if saved_engine in engine_options else 0
            
            tts_engine = st.radio(
                tr("tts.engine_selector"),
                engine_options,
                horizontal=True,
                format_func=lambda x: engine_labels.get(x, x),
                index=engine_default_index,
                key="digital_tts_local_engine"
            )
            
            # Variables for video generation
            tts_workflow_key = None
            ref_audio_path = None
            
            if tts_engine == "voxcpm_api":
                # VoxCPM API specific UI
                st.caption(tr("tts.engine.voxcpm_hint"))
                
                # VoxCPM parameters
                col1, col2 = st.columns(2)
                with col1:
                    voxcpm_cfg = st.slider(
                        tr("tts.voxcpm.cfg"),
                        min_value=1.0,
                        max_value=5.0,
                        value=local_config.get("voxcpm_cfg", 2.0),
                        step=0.1,
                        format="%.1f",
                        key="digital_tts_voxcpm_cfg"
                    )
                with col2:
                    voxcpm_normalize = st.checkbox(
                        tr("tts.voxcpm.normalize"),
                        value=local_config.get("voxcpm_normalize", False),
                        key="digital_tts_voxcpm_normalize"
                    )
                    voxcpm_denoise = st.checkbox(
                        tr("tts.voxcpm.denoise"),
                        value=local_config.get("voxcpm_denoise", False),
                        key="digital_tts_voxcpm_denoise"
                    )
                
                # 极致克隆模式 - Control instruction
                st.markdown(f"**{tr('tts.voxcpm.clone_mode')}**")
                control_instruction = st.text_input(
                    tr("tts.voxcpm.control_instruction"),
                    value="",
                    placeholder=tr("tts.voxcpm.control_instruction_placeholder"),
                    key="digital_tts_voxcpm_control_instruction"
                )
                
                # Prompt text for guided cloning
                col_pt1, col_pt2 = st.columns(2)
                with col_pt1:
                    use_prompt_text = st.checkbox(
                        tr("tts.voxcpm.use_prompt_text"),
                        value=False,
                        key="digital_tts_voxcpm_use_prompt_text"
                    )
                with col_pt2:
                    prompt_text = st.text_input(
                        tr("tts.voxcpm.prompt_text"),
                        value="",
                        placeholder=tr("tts.voxcpm.prompt_text_placeholder"),
                        key="digital_tts_voxcpm_prompt_text"
                    )
                
                # Reference audio for voice cloning (upload or history, preview inline)
                ref_audio_path, _ = render_upload_area(
                    category="ref_audio",
                    upload_label=tr("tts.ref_audio"),
                    accept_types=["mp3", "wav", "flac", "m4a", "aac", "ogg"],
                    accept_multiple=False,
                    upload_key="digital_tts_voxcpm_ref_audio",
                )
                
                selected_voice = None
                tts_speed = None
                
            else:
                # Edge TTS: Original voice + speed UI
                from pixelle_video.tts_voices import EDGE_TTS_VOICES, get_voice_display_name
                
                saved_voice = local_config.get("voice", "zh-CN-YunjianNeural")
                saved_speed = local_config.get("speed", 1.2)
                
                voice_options = []
                voice_ids = []
                default_voice_index = 0
                
                for idx, voice_config in enumerate(EDGE_TTS_VOICES):
                    voice_id = voice_config["id"]
                    display_name = get_voice_display_name(voice_id, tr, get_language())
                    voice_options.append(display_name)
                    voice_ids.append(voice_id)
                    
                    if voice_id == saved_voice:
                        default_voice_index = idx
                
                voice_col, speed_col = st.columns([1, 1])
                
                with voice_col:
                    selected_voice_display = st.selectbox(
                        tr("tts.voice_selector"),
                        voice_options,
                        index=default_voice_index,
                        key="digital_tts_local_voice"
                    )
                    selected_voice_index = voice_options.index(selected_voice_display)
                    selected_voice = voice_ids[selected_voice_index]
                
                with speed_col:
                    tts_speed = st.slider(
                        tr("tts.speed"),
                        min_value=0.5,
                        max_value=2.0,
                        value=saved_speed,
                        step=0.1,
                        format="%.1fx",
                        key="digital_tts_local_speed"
                    )
                    st.caption(tr("tts.speed_label", speed=f"{tts_speed:.1f}"))
            
            # Variables for video generation (ref_audio_path may already be set by VoxCPM block)
            tts_workflow_key = None
        
        # ================================================================
        # ComfyUI Mode UI
        # ================================================================
        else:  # comfyui mode
            tts_workflow_key = "runninghub/tts_index2.json"  # fallback
            
            # Reference audio for voice cloning (upload or history, preview inline)
            ref_audio_path, _ = render_upload_area(
                category="ref_audio",
                upload_label=tr("tts.ref_audio"),
                accept_types=["mp3", "wav", "flac", "m4a", "aac", "ogg"],
                accept_multiple=False,
                upload_key="digital_ref_audio_upload",
            )
            
            # Variables for video generation
            selected_voice = None
            tts_speed = None
        
        # ================================================================
        # TTS Preview (works for both modes)
        # ================================================================
        with st.expander(tr("tts.preview_title"), expanded=False):
            # Preview text input
            preview_text = st.text_input(
                tr("tts.preview_text"),
                value="大家好，这是一段测试语音。",
                placeholder=tr("tts.preview_text_placeholder"),
                key="digital_tts_preview_text"
            )
            
            # Preview button
            if st.button(tr("tts.preview_button"), key="gidital_preview_tts", use_container_width=True):
                with st.spinner(tr("tts.previewing")):
                    try:
                        # Build TTS params based on mode
                        tts_params = {
                            "text": preview_text,
                            "inference_mode": tts_mode
                        }
                        
                        if tts_mode == "local":
                            if tts_engine == "voxcpm_api":
                                tts_params["engine"] = "voxcpm_api"
                                tts_params["cfg"] = st.session_state.get("digital_tts_voxcpm_cfg", 2.0)
                                tts_params["normalize"] = st.session_state.get("digital_tts_voxcpm_normalize", False)
                                tts_params["denoise"] = st.session_state.get("digital_tts_voxcpm_denoise", False)
                                if ref_audio_path:
                                    tts_params["ref_audio"] = str(ref_audio_path)
                                # 极致克隆模式参数
                                control_val = st.session_state.get("digital_tts_voxcpm_control_instruction", "")
                                if control_val:
                                    tts_params["control_instruction"] = control_val
                                if st.session_state.get("digital_tts_voxcpm_use_prompt_text", False):
                                    tts_params["use_prompt_text"] = True
                                    prompt_val = st.session_state.get("digital_tts_voxcpm_prompt_text", "")
                                    if prompt_val:
                                        tts_params["prompt_text"] = prompt_val
                            else:
                                tts_params["engine"] = "edge_tts"
                                tts_params["voice"] = selected_voice
                                tts_params["speed"] = tts_speed
                        else:  # comfyui
                            tts_params["workflow"] = tts_workflow_key
                            if ref_audio_path:
                                tts_params["ref_audio"] = str(ref_audio_path)
                        
                        audio_path = run_async(pixelle_video.tts(**tts_params))
                        
                        # Play the audio
                        if audio_path:
                            st.success(tr("tts.preview_success"))
                            if os.path.exists(audio_path):
                                st.audio(audio_path, format="audio/mp3")
                            elif audio_path.startswith('http'):
                                st.audio(audio_path)
                            else:
                                st.error("Failed to generate preview audio")
                            
                            # Show file path
                            st.caption(f"📁 {audio_path}")
                        else:
                            st.error("Failed to generate preview audio")
                    except Exception as e:
                        st.error(tr("tts.preview_failed", error=str(e)))
                        logger.exception(e)
    
    # Return all style configuration parameters (Simplified version only local TTS)
    return {
        "tts_inference_mode": tts_mode,
        "tts_engine": tts_engine if tts_mode == "local" else None,
        "tts_voice": selected_voice if tts_mode == "local" else None,
        "tts_speed": tts_speed if tts_mode == "local" else None,
        "tts_workflow": tts_workflow_key if tts_mode == "comfyui" else None,
        "ref_audio": str(ref_audio_path) if ref_audio_path else None,
        # VoxCPM params for digital human pipeline (read from session_state once here)
        "voxcpm_cfg": st.session_state.get("digital_tts_voxcpm_cfg", 2.0) if tts_mode == "local" and tts_engine == "voxcpm_api" else None,
        "voxcpm_normalize": st.session_state.get("digital_tts_voxcpm_normalize", False) if tts_mode == "local" and tts_engine == "voxcpm_api" else False,
        "voxcpm_denoise": st.session_state.get("digital_tts_voxcpm_denoise", False) if tts_mode == "local" and tts_engine == "voxcpm_api" else False,
        "voxcpm_control_instruction": st.session_state.get("digital_tts_voxcpm_control_instruction", ""),
        "voxcpm_use_prompt_text": st.session_state.get("digital_tts_voxcpm_use_prompt_text", False),
        "voxcpm_prompt_text": st.session_state.get("digital_tts_voxcpm_prompt_text", ""),
    }
