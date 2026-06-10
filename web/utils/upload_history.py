"""
Upload history management for Web UI

Stores uploaded file references in a JSON file so records
survive page refresh and server restart. Users can re-use
previously uploaded character images, product images,
and reference audio files without re-uploading.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import streamlit as st
from loguru import logger

# Session state key
_SESSION_KEY = "_upload_history_store"

# Supported file categories
UploadCategory = Literal["character_image", "goods_image", "ref_audio"]

# JSON file path for persistence
_HISTORY_FILE = Path("temp/upload_history.json")


def _load_from_file() -> list[dict]:
    """Load upload history from JSON file."""
    try:
        if _HISTORY_FILE.exists():
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception as e:
        logger.warning(f"Failed to load upload history file: {e}")
    return []


def _save_to_file(records: list[dict]):
    """Save upload history to JSON file."""
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save upload history file: {e}")


def _ensure_store():
    """Initialize upload history from file into session_state."""
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = _load_from_file()


def _get_store() -> list[dict]:
    """Get the upload history store list."""
    _ensure_store()
    return st.session_state[_SESSION_KEY]


def record_upload(category: UploadCategory, name: str, path: str) -> str:
    """
    Record a newly uploaded file into history (persisted to file).

    Args:
        category: File category (character_image, goods_image, ref_audio)
        name: Original file name
        path: Absolute path to the saved file

    Returns:
        The record id
    """
    store = _get_store()
    record_id = str(uuid.uuid4())[:8]
    record = {
        "id": record_id,
        "category": category,
        "name": name,
        "path": path,
        "timestamp": datetime.now().isoformat(),
    }
    store.append(record)
    # Persist to file immediately
    _save_to_file(store)
    logger.debug(f"Recorded upload: [{category}] {name} -> {path}")
    return record_id


def get_history_by_category(category: UploadCategory) -> list[dict]:
    """
    Get all upload records for a specific category (newest first).

    Args:
        category: File category to filter by

    Returns:
        List of matching records
    """
    store = _get_store()
    records = [r for r in store if r["category"] == category]
    records.reverse()  # newest first
    return records


def delete_record(record_id: str) -> bool:
    """
    Delete a history record by its id.
    Also removes the associated file from disk.

    Args:
        record_id: The record id to delete

    Returns:
        True if deleted, False if not found
    """
    store = _get_store()
    for i, r in enumerate(store):
        if r["id"] == record_id:
            removed = store.pop(i)
            _save_to_file(store)
            # Try to delete the physical file
            try:
                p = Path(removed["path"])
                if p.exists():
                    p.unlink()
                    logger.debug(f"Deleted file: {p}")
            except Exception as e:
                logger.warning(f"Failed to delete file {removed.get('path')}: {e}")
            logger.debug(f"Deleted upload record: {record_id}")
            return True
    return False


def _get_upload_dir(category: UploadCategory) -> Path:
    """Get the persistent upload directory for a category."""
    # Map categories to subdirectory names
    cat_map = {
        "character_image": "character",
        "goods_image": "goods",
        "ref_audio": "audio",
    }
    dir_name = cat_map.get(category, "misc")
    upload_dir = Path(f"temp/uploads/{dir_name}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def render_upload_area(
    category: UploadCategory,
    upload_label: str,
    accept_types: list[str],
    accept_multiple: bool = False,
    upload_key: str = "",
    history_label: str = "从历史选择",
) -> tuple[Optional[str], list[str]]:
    """
    Render a combined upload + history selection area.
    始终显示「上传新文件」和「从历史选择」两个选项。
    历史记录持久化到文件，刷新/重启不丢失。

    Args:
        category: Upload category
        upload_label: Label for the file uploader
        accept_types: List of accepted file extensions
        accept_multiple: Whether to accept multiple files
        upload_key: Key for the file_uploader widget
        history_label: Label for history selection tab

    Returns:
        (selected_path, all_paths) where:
        - selected_path is the latest single file path for reference audio
        - all_paths is the list of all paths (for character/goods images)
    """
    history_records = get_history_by_category(category)
    has_history = len(history_records) > 0

    # 始终显示两个选项，让用户自由选择
    source_tab = st.radio(
        "选择方式",
        ["upload", "history"],
        horizontal=True,
        format_func=lambda x: "📤 上传新文件" if x == "upload" else "📂 从历史选择",
        key=f"upload_source_tab_{category}_{upload_key}",
        label_visibility="collapsed",
    )

    selected_path: Optional[str] = None
    all_paths: list[str] = []

    if source_tab == "upload":
        uploaded_files = st.file_uploader(
            upload_label,
            type=accept_types,
            accept_multiple_files=accept_multiple,
            key=f"upload_area_{category}_{upload_key}",
        )

        if uploaded_files:
            upload_dir = _get_upload_dir(category)

            for uploaded_file in (uploaded_files if accept_multiple else [uploaded_files]):
                # Use original filename, add timestamp suffix to avoid overwrites
                stem = Path(uploaded_file.name).stem
                suffix = Path(uploaded_file.name).suffix
                import uuid as _uuid
                unique_name = f"{stem}_{str(_uuid.uuid4())[:6]}{suffix}"
                file_path = upload_dir / unique_name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                abs_path = str(file_path.absolute())
                all_paths.append(abs_path)
                record_upload(category, uploaded_file.name, abs_path)
                # For single-file categories (audio), track it
                if not accept_multiple:
                    selected_path = abs_path
    else:
        # History tab
        if not has_history:
            st.info("暂无历史上传记录，请先上传文件。")
        else:
            # Build id map for deletion
            id_map: dict[str, str] = {}  # id -> path
            name_map: dict[str, str] = {}  # id -> name
            for r in history_records:
                id_map[r["id"]] = r["path"]
                name_map[r["id"]] = r["name"]

            options = []
            display_map = {}
            for r in history_records:
                try:
                    ts = datetime.fromisoformat(r["timestamp"]).strftime("%m-%d %H:%M")
                except Exception:
                    ts = r["timestamp"][:16] if len(r["timestamp"]) >= 16 else r["timestamp"]
                display = f"[{ts}] {r['name']}"
                options.append(display)
                display_map[display] = (r["id"], r["path"])

            selected_display = st.selectbox(
                "选择历史记录",
                options=options,
                key=f"upload_history_select_{category}_{upload_key}",
            )

            if selected_display:
                record_id, file_path = display_map.get(selected_display, (None, None))
                if file_path and Path(file_path).exists():
                    selected_path = file_path
                    all_paths.append(file_path)

                    # Show selected file preview + delete button
                    col_preview, col_del = st.columns([4, 1])
                    with col_preview:
                        if category == "ref_audio":
                            st.audio(file_path)
                        else:
                            st.image(file_path, caption=Path(file_path).name, width=200)
                    with col_del:
                        if st.button("🗑️ 删除", key=f"del_history_{category}_{record_id}", use_container_width=True):
                            delete_record(record_id)
                            st.rerun()
                elif file_path and not Path(file_path).exists():
                    st.warning(f"文件已不存在: {file_path}")
                    # Show delete button for broken records too
                    if st.button("🗑️ 删除此记录", key=f"del_history_broken_{category}_{record_id}", use_container_width=True):
                        delete_record(record_id)
                        st.rerun()

    return selected_path, all_paths