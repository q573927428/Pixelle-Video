"""Rebuild .tasks_index.json from running API server tasks (minimal TaskCenterView fields)"""
import requests
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"
INDEX_FILE = OUTPUT_DIR / ".tasks_index.json"

# Fields used by TaskCenterView.vue
REQUEST_PARAMS_FIELDS = {"character_assets", "goods_assets", "goods_title", "goods_text", "_runninghub_task_id"}


def main():
    try:
        r = requests.get("http://localhost:8000/api/tasks", timeout=5)
        tasks_raw = r.json()
    except Exception as e:
        print(f"❌ Failed to fetch tasks from API: {e}")
        print("   Make sure the API server is running on http://localhost:8000")
        return

    tasks = []
    for t in tasks_raw:
        # Only keep request_params fields used by the UI
        request_params = {}
        raw_params = t.get("request_params") or {}
        for key in REQUEST_PARAMS_FIELDS:
            if key in raw_params:
                request_params[key] = raw_params[key]

        task = {
            "task_id": t.get("task_id"),
            "task_type": t.get("task_type"),
            "status": t.get("status"),
            "user_id": t.get("user_id"),
            "created_at": t.get("created_at"),
            "started_at": t.get("started_at"),
            "completed_at": t.get("completed_at"),
            "error": t.get("error"),
            "warnings": t.get("warnings", []),
            "request_params": request_params or None,
        }
        tasks.append(task)

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "version": "1.0",
            "tasks": tasks,
            "last_updated": None,
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ Rebuilt {INDEX_FILE}")
    print(f"   Total tasks: {len(tasks)}")


if __name__ == "__main__":
    main()