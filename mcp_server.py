"""Bob's local MCP interface, using the official MCP v1 SDK."""
from mcp.server.fastmcp import FastMCP
from cutover.engine import load_case, load_plan, repair_brief
from cutover.service import run_rehearsal, validate_imported_contract

mcp = FastMCP('Cutover')


@mcp.tool()
def inspect_release(case: str = 'parcel') -> dict:
    """Read the fixed old-version contract and the failing rename candidate. Cases: parcel, contacts."""
    return {'contract': load_case(case), 'candidate': load_plan(case, 'rename'),
            'rules': 'Propose changed SQL in rehearse_candidate; never modify the fixed old contract or evaluator.'}


@mcp.tool()
def inspect_imported_contract(contract: dict) -> dict:
    """Validate a supplied single-table SQLite contract before asking Bob to repair it.

    Returns its fingerprint and size. SQL runs only in the bounded disposable worker.
    Do not provide private production schemas to a hosted Bob session.
    """
    return validate_imported_contract(contract)


@mcp.tool()
def rehearse_candidate(case: str, name: str, migration: str, read: str, write: str,
                       insert: str, contract: dict | None = None) -> dict:
    """Execute a proposed SQLite migration and new adapter against fixed old/new schedules in disposable databases.

    For case='custom', supply the validated contract object on every call; bundled cases
    reject it. SQL only; no shell execution, repo changes, credentials or production access.
    Returns measured counts and a shortest observed counterexample. A pass is bounded to the suite.
    """
    report = run_rehearsal(case, {'name': name, 'migration': migration, 'read': read,
                                  'write': write, 'insert': insert}, contract)
    return {key: value for key, value in report.items() if key != 'results'}


@mcp.tool()
def diagnose_reference(case: str = 'parcel', reference: str = 'rename') -> dict:
    """Execute a bundled example and return a repair brief with concrete expected/actual evidence.

    Failing references are rename, backfill, late_bridge. Passing examples are withheld from this diagnostic tool.
    """
    if reference not in ('rename', 'backfill', 'late_bridge'):
        raise ValueError('Only failing references are available through this diagnostic tool.')
    return repair_brief(run_rehearsal(case, load_plan(case, reference)))


if __name__ == '__main__':
    mcp.run(transport='stdio')
