"""Clean up incomplete task folders without metadata.json"""
import shutil
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# System directories that are NOT task folders and should be preserved
SYSTEM_DIRS = {"api", "api_images"}


def main():
    deleted = 0
    kept = 0

    for item in sorted(OUTPUT_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        # Preserve system directories
        if item.name in SYSTEM_DIRS:
            kept += 1
            print(f"  ✓ KEPT   {item.name} (system directory)")
            continue

        metadata_path = item / "metadata.json"
        if metadata_path.exists():
            kept += 1
            print(f"  ✓ KEPT   {item.name} (has metadata.json)")
        else:
            shutil.rmtree(item)
            deleted += 1
            print(f"  ✗ DELETE {item.name} (no metadata.json)")

    print(f"\n✅ Done! Deleted {deleted} incomplete folders, kept {kept} folders.")


if __name__ == "__main__":
    main()