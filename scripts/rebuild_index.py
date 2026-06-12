"""Rebuild the task index from existing directories"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pixelle_video.services.persistence import PersistenceService


async def main():
    p = PersistenceService()
    await p.rebuild_index()
    stats = await p.get_statistics()
    print(f"Index rebuilt. Total tasks: {stats['total_tasks']}")


asyncio.run(main())