"""Editor 启动入口 —— 通过 `Editor.exe --runpython boot.py` 加载。

职责：
    1. 解析 --runpythonargs（端口、token 等）
    2. 把本包加进 sys.path
    3. 配置日志
    4. 安装 threading_bridge（注册 tick pump）
    5. 在后台线程启动 asyncio loop，跑 mcp_server.serve()
    6. **返回**，让 Editor 继续正常运行；MCP Server 在后台响应请求

注意：这个脚本**不能阻塞**主线程。Editor --runpython 是同步调的，boot.py 返回
后 Editor 才继续走启动流程。所以 asyncio.run() 必须在 worker 线程里。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from pathlib import Path


_HERE = Path(__file__).resolve().parent
# 让 `import o3de_mcp` 能用 —— 我们让父目录进 path，包名就是目录名
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# 允许用 `from o3de_mcp import ...` 或包内相对导入都工作
_PACKAGE = _HERE.name  # 'o3de_mcp'


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="o3de_mcp.boot")
    p.add_argument("--host", default=None, help="override MCP_HOST")
    p.add_argument("--port", type=int, default=None, help="override MCP_PORT")
    p.add_argument("--auth-token", default=None, help="override MCP_AUTH_TOKEN (env)")
    p.add_argument("--log-level", default=None, help="INFO / DEBUG / WARNING")
    return p.parse_args(argv)


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    if args.host:
        os.environ["MCP_HOST"] = args.host
    if args.port:
        os.environ["MCP_PORT"] = str(args.port)
    if args.auth_token:
        os.environ["MCP_AUTH_TOKEN"] = args.auth_token
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level.upper()


def _start_server_thread(server_coro_factory) -> threading.Thread:
    """在新线程里起 asyncio loop，跑 server 协程。"""
    import asyncio as _asyncio

    def _runner():
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server_coro_factory())
        except Exception:
            logging.exception("MCP server thread crashed")
        finally:
            loop.close()

    t = threading.Thread(target=_runner, name="o3de_mcp_asyncio", daemon=True)
    t.start()
    return t


def main(argv: list[str] | None = None) -> int:
    # sys.argv 在 --runpythonargs 下：[script, ...args]
    # 跳过脚本名
    if argv is None:
        argv = sys.argv[1:] if len(sys.argv) > 1 else []

    args = _parse_args(argv)

    # 先读 .env → 再应用 CLI override（CLI 优先）
    _apply_cli_overrides(args)

    log_level = args.log_level or os.environ.get("LOG_LEVEL", "INFO")
    _configure_logging(log_level)

    log = logging.getLogger("o3de_mcp.boot")
    log.info("o3de_mcp boot starting (pid=%s)", os.getpid())

    # 懒导入 —— 必须在 sys.path 调整好之后
    from o3de_mcp import config, mcp_server, threading_bridge

    config.load()
    log.info(config.summary())

    if not config.AUTH_TOKEN and config.HOST != "127.0.0.1":
        log.warning(
            "!! MCP_AUTH_TOKEN is empty and host is %s —— anyone on the network "
            "can control this editor. Set MCP_AUTH_TOKEN or bind to 127.0.0.1 only.",
            config.HOST,
        )

    # 安装跨线程桥（必须先调，handler 才能 call_on_main）
    threading_bridge.install()
    log.info("threading_bridge pump_mode=%s", threading_bridge.pump_mode())

    # 启 asyncio server thread
    _start_server_thread(mcp_server.serve)

    log.info(
        "MCP Server starting on http://%s:%s/sse (health: /health)",
        config.HOST, config.PORT,
    )
    log.info("boot.py returning — Editor resumes normal operation")
    return 0


# EditorPythonBindings --runpython 的执行模式：
#   1) 直接把脚本当 module 跑，`__name__ == '__main__'`
#   2) 某些版本里 __name__ 不同，两种都保险
if __name__ in ("__main__", "__builtin__", "builtins"):
    main()
