"""Run with the interpreter containing requirements-mcp.txt. Real stdio protocol check."""
import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'mcp_server.py')], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {'inspect_release', 'rehearse_candidate', 'diagnose_reference'}
            inspect = await session.call_tool('inspect_release', {'case': 'parcel'})
            assert not inspect.isError
            broken = await session.call_tool('diagnose_reference', {'case': 'parcel', 'reference': 'backfill'})
            assert not broken.isError
            plan = json.loads((ROOT / 'examples' / 'parcel' / 'bridge.json').read_text())
            result = await session.call_tool('rehearse_candidate', {'case': 'parcel', **plan})
            assert not result.isError
            content = json.loads(next(c.text for c in result.content if c.type == 'text'))
            assert content['passed'] == 124
            assert content['bob']['verified'] is False
            invalid = await session.call_tool('inspect_release', {'case': '../anything'})
            assert invalid.isError
            print('PASS: MCP initialize, tool discovery, inspect, diagnose, candidate execution and invalid-input handling.')
            print('SDK client verified; IBM Bob host session remains unverified.')


asyncio.run(main())
