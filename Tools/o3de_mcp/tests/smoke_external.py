"""External MCP client smoke test —— 用官方 mcp SDK 作为 client 连进去测。

用法：
    # 先确保 Editor 已经带 --runpython boot.py 启动，监听 24601
    python -m o3de_mcp.tests.smoke_external

需要装：
    pip install mcp
"""

from __future__ import annotations

import asyncio
import json
import os
import sys


HOST = os.environ.get("MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_PORT", "24601"))
TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")

URL = f"http://{HOST}:{PORT}/sse"


async def main() -> int:
    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
    except ImportError:
        print("ERROR: mcp SDK not installed. pip install mcp")
        return 2

    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    print(f"Connecting to {URL} ...")

    async with sse_client(URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✓ MCP handshake OK")

            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"✓ list_tools → {len(tool_names)} tools")
            for n in tool_names:
                print(f"    - {n}")

            # call entity.create
            r = await session.call_tool("entity.create", {"name": "ExtSmoke"})
            payload = _first_text(r)
            print(f"✓ entity.create → {payload}")
            eid = payload.get("entity_id")
            if not eid:
                print("FAIL: no entity_id in create result")
                return 1

            # call query.find_by_name
            r = await session.call_tool(
                "query.find_by_name", {"name": "ExtSmoke", "exact": True}
            )
            print(f"✓ query.find_by_name → {_first_text(r)}")

            # optional delete
            os.environ.setdefault("MCP_SMOKE_DELETE", "0")
            if os.environ["MCP_SMOKE_DELETE"] == "1":
                r = await session.call_tool("entity.delete", {"entity_id": eid})
                print(f"✓ entity.delete → {_first_text(r)}")

    print("ALL GREEN.")
    return 0


def _first_text(result) -> dict:
    """从 MCP CallToolResult 拿第一个 TextContent 并 JSON decode。"""
    for c in result.content:
        if getattr(c, "type", None) == "text":
            try:
                return json.loads(c.text)
            except Exception:
                return {"_raw": c.text}
    return {}


if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except KeyboardInterrupt:
        rc = 130
    except Exception as e:
        print(f"ERROR: {e}")
        rc = 1
    sys.exit(rc)
