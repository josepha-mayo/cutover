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
            assert {t.name for t in tools.tools} == {
                'inspect_release', 'inspect_imported_contract',
                'rehearse_candidate', 'diagnose_reference'}
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
            warehouse = ROOT / 'examples' / 'warehouse'
            contract = json.loads((warehouse / 'contract.json').read_text(encoding='utf-8'))
            late = json.loads((warehouse / 'late_bridge.json').read_text(encoding='utf-8'))
            validated = await session.call_tool('inspect_imported_contract', {'contract': contract})
            assert not validated.isError
            meta = json.loads(next(c.text for c in validated.content if c.type == 'text'))
            assert meta['status'] == 'valid'
            custom = await session.call_tool('rehearse_candidate', {
                'case': 'custom', 'contract': contract, **late})
            assert not custom.isError
            result = json.loads(next(c.text for c in custom.content if c.type == 'text'))
            assert result['status'] == 'blocked' and result['passed'] == 108
            assert result['contract_hash'] == meta['contract_hash']
            replacement = await session.call_tool('rehearse_candidate', {
                'case': 'parcel', 'contract': contract, **plan})
            assert replacement.isError
            invalid = await session.call_tool('inspect_release', {'case': '../anything'})
            assert invalid.isError
            withheld = await session.call_tool('diagnose_reference', {'case': 'parcel', 'reference': 'bridge'})
            assert withheld.isError
            print('PASS: MCP discovery, bundled and imported contract execution, diagnosis and invalid-input handling.')
            print('SDK client verified; IBM Bob host session remains unverified.')


asyncio.run(main())
