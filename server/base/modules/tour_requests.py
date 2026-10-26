"""Serialize dialogue memory updates and abandon disconnected HTTP turns."""
import asyncio
from contextlib import suppress
from weakref import WeakValueDictionary

_locks = WeakValueDictionary()

async def run_turn(session_id, request, operation):
    lock = _locks.setdefault(session_id, asyncio.Lock())
    async def guarded():
        async with lock:
            return await operation()
    task = asyncio.create_task(guarded())
    try:
        while not task.done():
            if request is not None and await request.is_disconnected():
                task.cancel()
                raise asyncio.CancelledError()
            await asyncio.wait({task}, timeout=.2)
        return await task
    finally:
        if not task.done(): task.cancel()
        with suppress(asyncio.CancelledError): await task
