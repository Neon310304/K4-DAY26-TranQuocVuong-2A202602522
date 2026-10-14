"""Client test cho versioned_server.py — gọi cả tool v1, v2 và đọc server metadata."""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> dict:
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("versioned_server.py"))])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Đọc server metadata
            info = await session.read_resource("server://info")
            meta = json.loads(info.contents[0].text)
            print(f"Server: {meta['name']} v{meta['version']}")
            print(f"Deprecated tools: {meta['deprecated_tools']}")
            print(f"Migration: {meta['migration_guide']}\n")

            # 2. Liệt kê tools
            tools = await session.list_tools()
            print("Tools:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")
            print()

            # 3. Gọi tool v1 (deprecated nhưng vẫn hoạt động)
            r1 = await session.call_tool("get_weather", {"city": "Hanoi"})
            if r1.is_error:
                raise RuntimeError("Legacy tool returned an error")
            print(f"[v1] get_weather('Hanoi'):\n  {r1.content[0].text}\n")

            # 4. Gọi tool v2
            r2 = await session.call_tool("get_weather_v2", {
                "city": "Hanoi",
                "include_forecast": True,
                "units": "celsius",
            })
            if r2.is_error:
                raise RuntimeError("V2 tool returned an error")
            print(f"[v2] get_weather_v2('Hanoi', forecast=True):")
            print(f"  {json.dumps(json.loads(r2.content[0].text), indent=2, ensure_ascii=False)}")
            default = await session.call_tool("get_weather_v2", {"city": "Hanoi"})
            if default.is_error:
                raise RuntimeError("V2 default arguments returned an error")

    root = Path(__file__).resolve().parents[1]
    sources = ["03-production/versioned_client.py", "03-production/versioned_server.py"]
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "status": "passed",
            "scope": "actual_mcp_stdio_v1_v2_defaults_and_metadata_no_llm", "metadata": meta,
            "tools": [{"name": t.name, "input_schema": t.input_schema} for t in tools.tools],
            "v1": {"is_error": r1.is_error, "result": r1.content[0].text},
            "v2_forecast": {"is_error": r2.is_error, "result": json.loads(r2.content[0].text)},
            "v2_defaults": {"is_error": default.is_error, "result": json.loads(default.content[0].text)},
            "source_hashes": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(main())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
