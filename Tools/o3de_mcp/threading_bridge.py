"""Worker 线程 ↔ Editor 主线程的跨线程调用桥。

核心问题：
    - asyncio HTTP server 必须跑在 Python 线程（否则阻塞 Editor UI）
    - azlmbr 的 EBus 调用大部分必须在 Editor 主线程（不 thread-safe）
    → 需要 worker 线程把 "要跑的 Python 函数" 塞进队列，主线程每帧取出来跑，
       结果塞回 asyncio.Future。

实现两条路径，由 `install()` 按可用性选一条：

    **路径 A（首选）**：Editor TickBus 订阅
        在主线程注册一个 tick 回调，每帧 drain pending queue。
        需要 azlmbr.tick 或 azlmbr.bus 对 Tick Notification 的 Python 订阅支持。

    **路径 B（fallback）**：另一 worker 线程轮询 + idle_wait_frames
        新开一个 "pump" 线程，在循环里 `general.idle_wait_frames(0)`
        （这个 API 会把控制权让给 Editor 一帧）然后从队列取任务。
        缺点是占一个 Python 线程，且不保证 idle_wait_frames 真的让主线程跑。

    真跑时如果 A 不通，自动降到 B。都不通就抛错给 boot.py。

用法：

    from . import threading_bridge as tb
    tb.install()                              # 只调一次，在主线程

    # 在 worker / asyncio handler 里：
    def work():
        # 这里保证跑在 Editor 主线程
        import azlmbr.editor as editor
        return editor.ToolsApplicationRequestBus(...)

    result = await tb.call_on_main(work)      # 带 timeout
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from typing import Any, Callable, Optional

from . import config
from .errors import MCPToolError, CODE_TIMEOUT

log = logging.getLogger(__name__)


# (fn, args, kwargs, future, loop)
_PendingItem = tuple


_pending: "queue.Queue[_PendingItem]" = queue.Queue()
_installed = False
_pump_mode: str = "none"  # "tick" / "thread" / "none"


# ---------------------------------------------------------------- public API

def install() -> None:
    """一次性初始化。必须在 Editor 主线程调（即 --runpython boot.py 的当前线程）。"""
    global _installed, _pump_mode
    if _installed:
        return

    # 尝试路径 A：Tick Bus 订阅
    if _try_install_tick_handler():
        _pump_mode = "tick"
        log.info("threading_bridge: using EditorTickBus pump")
    else:
        # 路径 B：fallback 到轮询线程
        _start_polling_pump()
        _pump_mode = "thread"
        log.warning("threading_bridge: EditorTickBus unavailable, fell back to polling thread")

    _installed = True


def pump_mode() -> str:
    return _pump_mode


async def call_on_main(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """从任何 worker 线程（或 asyncio handler）调用；
    把 fn 调度到 Editor 主线程执行，await 结果。
    """
    if not _installed:
        raise RuntimeError("threading_bridge.install() not called")

    if _pending.qsize() > config.MAX_PENDING_QUEUE:
        raise MCPToolError(
            "overloaded",
            f"Pending queue full ({config.MAX_PENDING_QUEUE}); Editor may be stuck.",
        )

    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    _pending.put((fn, args, kwargs, fut, loop))

    try:
        return await asyncio.wait_for(fut, timeout=config.TOOL_CALL_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        raise MCPToolError(
            CODE_TIMEOUT,
            f"Tool call timed out after {config.TOOL_CALL_TIMEOUT_SEC}s (Editor stuck?)",
        )


# ---------------------------------------------------------------- pump core

def _pump_once() -> int:
    """主线程调用：drain 一轮 pending queue。返回处理数量。"""
    processed = 0
    while True:
        try:
            item = _pending.get_nowait()
        except queue.Empty:
            return processed
        fn, args, kwargs, fut, loop = item
        try:
            result = fn(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001
            if not fut.cancelled():
                loop.call_soon_threadsafe(fut.set_exception, e)
        else:
            if not fut.cancelled():
                loop.call_soon_threadsafe(fut.set_result, result)
        processed += 1
        # 防一个 tick 里被无限队列淹死
        if processed >= 32:
            return processed


# ---------------------------------------------------------------- path A: tick bus

def _try_install_tick_handler() -> bool:
    """尝试订阅 Editor/System TickBus，返回是否成功。"""
    try:
        # 不同 O3DE 版本 API 略不同；按优先级试：
        # 1) azlmbr.tick.TickBus Notification（handler 类型）
        # 2) azlmbr.editor.EditorTickBus
        # 3) azlmbr.bus.SystemTickBus
        #
        # 这里用 NotificationBusHandler pattern。如果该版本的 Python
        # binding 不支持我们要订阅的 bus，会抛，就降级。
        import azlmbr.bus as _bus  # type: ignore[import]

        # O3DE 里通用的 tick 入口试一个：
        try:
            import azlmbr.editor as _editor  # type: ignore[import]
            EditorTickBus = getattr(_editor, "EditorTickBus", None)
            if EditorTickBus is not None:
                handler = EditorTickBus()
                if hasattr(handler, "connect"):
                    handler.connect()
                    handler.add_callback("OnTick", _on_tick_callback)
                    _keep_ref(handler)
                    return True
        except Exception as e:
            log.debug("EditorTickBus not usable: %s", e)

        # 退而求其次：尝试 SystemTickBus
        try:
            # 某些 O3DE 版本在 azlmbr.bus 里直接有 SystemTickBus Notification
            SystemTickBus = getattr(_bus, "SystemTickBus", None)
            if SystemTickBus is not None:
                handler = SystemTickBus()
                if hasattr(handler, "connect"):
                    handler.connect()
                    handler.add_callback("OnSystemTick", _on_tick_callback)
                    _keep_ref(handler)
                    return True
        except Exception as e:
            log.debug("SystemTickBus not usable: %s", e)

        return False
    except Exception as e:
        log.debug("tick install failed: %s", e)
        return False


_handler_refs: list = []


def _keep_ref(obj: Any) -> None:
    """Python GC 会回收临时 handler 对象，必须全局引用一下。"""
    _handler_refs.append(obj)


def _on_tick_callback(*args, **kwargs) -> None:  # noqa: ARG001
    try:
        _pump_once()
    except Exception:
        log.exception("tick pump failed")


# ---------------------------------------------------------------- path B: polling thread

def _start_polling_pump() -> None:
    """fallback：启一个 daemon 线程，循环 idle_wait_frames(0) 让出一帧，然后 pump_once。

    注意：这里假设 azlmbr.legacy.general.idle_wait_frames() 会把控制权真正交给
    Editor 主线程执行渲染/tick；如果不是这样，整个方案退化成 busy wait。
    """
    def _loop() -> None:
        try:
            import azlmbr.legacy.general as _general  # type: ignore[import]
            idle = getattr(_general, "idle_wait_frames", None)
        except Exception:
            idle = None

        while True:
            _pump_once()
            if idle is not None:
                try:
                    idle(0)
                except Exception:
                    time.sleep(0.01)
            else:
                time.sleep(0.01)

    t = threading.Thread(target=_loop, name="o3de_mcp_pump", daemon=True)
    t.start()


# ---------------------------------------------------------------- sync version (supplier for sync contexts)

def call_on_main_sync(fn: Callable[..., Any], *args, timeout: Optional[float] = None, **kwargs) -> Any:
    """同步版本：用 threading.Event，不走 asyncio。给少数必须同步的场景。"""
    if not _installed:
        raise RuntimeError("threading_bridge.install() not called")

    done = threading.Event()
    holder: dict = {}

    def _shim():
        try:
            holder["result"] = fn(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001
            holder["exc"] = e
        finally:
            done.set()

    class _FakeFuture:
        def __init__(self):
            pass

        def cancelled(self):
            return False

        def set_result(self, v):
            done.set()

        def set_exception(self, e):
            done.set()

    class _FakeLoop:
        def call_soon_threadsafe(self, cb, *args):
            cb(*args)

    _pending.put((_shim, (), {}, _FakeFuture(), _FakeLoop()))
    if not done.wait(timeout or config.TOOL_CALL_TIMEOUT_SEC):
        raise MCPToolError(CODE_TIMEOUT, "sync tool call timed out")
    if "exc" in holder:
        raise holder["exc"]
    return holder.get("result")
