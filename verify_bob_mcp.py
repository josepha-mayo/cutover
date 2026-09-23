"""Check a frozen Bob workspace's configured MCP server with the official SDK.

Run verify_bob_session.py first. This is a local connectivity check, never
evidence that IBM Bob itself used the server or authored a candidate.
"""
import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(workspace):
    settings = json.loads((workspace / '.bob' / 'mcp.json').read_text(encoding='utf-8'))
    server = settings['mcpServers']['cutover']
    assert server['disabled'] is False
    assert Path(server['cwd']).resolve() == workspace
    assert Path(server['args'][0]).resolve() == workspace / 'mcp_server.py'
    params = StdioServerParameters(
        command=server['command'], args=server['args'], cwd=server['cwd'])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == {'inspect_release', 'diagnose_reference', 'rehearse_candidate'}, names
            inspected = await session.call_tool('inspect_release', {'case': 'parcel'})
            assert not inspected.isError
            diagnosis = await session.call_tool(
                'diagnose_reference', {'case': 'parcel', 'reference': 'late_bridge'})
            assert not diagnosis.isError
            brief = json.loads(next(item.text for item in diagnosis.content if item.type == 'text'))
            witness = brief['shortest_observed_witness']
            assert witness['id'] == 'window_write_after_2-0', witness['id']
            withheld = await session.call_tool(
                'diagnose_reference', {'case': 'parcel', 'reference': 'bridge'})
            assert withheld.isError
            return {'status': 'pass', 'workspace': str(workspace),
                    'tools': sorted(names), 'late_bridge_witness': witness['id'],
                    'passing_reference_withheld': True,
                    'bob_host_session_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    result = asyncio.run(asyncio.wait_for(check(workspace), timeout=60))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
