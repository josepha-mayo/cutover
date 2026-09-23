"""Bob's local MCP interface, using the official MCP v1 SDK."""
from mcp.server.fastmcp import FastMCP
from cutover.engine import load_case, load_plan, repair_brief
from cutover.service import run_rehearsal

mcp = FastMCP('Cutover')


@mcp.tool()
def inspect_release(case: str = 'parcel') -> dict:
    """Read the fixed old-version contract and the failing rename candidate. Cases: parcel, contacts."""
    return {'contract': load_case(case), 'candidate': load_plan(case, 'rename'),
            'rules': 'Propose changed SQL in rehearse_candidate; never modify the fixed old contract or evaluator.'}


@mcp.tool()
def rehearse_candidate(case: str, name: str, migration: str, read: str, write: str, insert: str) -> dict:
    """Execute a proposed SQLite migration and new adapter against fixed old/new schedules in disposable databases.

    SQL only; no shell execution, repo changes, credentials or production access. Returns measured
    counts and a shortest observed counterexample. A pass is bounded to the reported suite.
    """
    report = run_rehearsal(case, {'name': name, 'migration': migration, 'read': read, 'write': write, 'insert': insert})
    return {key: value for key, value in report.items() if key != 'results'}


@mcp.tool()
def diagnose_reference(case: str = 'parcel', reference: str = 'rename') -> dict:
    """Execute a bundled example and return a repair brief with concrete expected/actual evidence.

    References are rename, backfill, late_bridge, bridge. Bridge is a prewritten reference solution, never a claim of Bob authorship.
    """
    return repair_brief(run_rehearsal(case, load_plan(case, reference)))


if __name__ == '__main__':
    mcp.run(transport='stdio')
