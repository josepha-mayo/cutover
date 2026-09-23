"""Create project-local Bob MCP configuration with explicit interpreter paths."""
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--python', type=Path, default=Path(sys.executable), help='Interpreter with requirements-mcp.txt installed')
args = parser.parse_args()
root = Path(__file__).resolve().parent
executable = args.python.resolve()
if not executable.is_file():
    parser.error('Interpreter does not exist')
destination = root / '.bob' / 'mcp.json'
config = json.loads(destination.read_text()) if destination.exists() else {}
config.setdefault('mcpServers', {})['cutover'] = {
    'command': str(executable), 'args': [str(root / 'mcp_server.py')],
    'cwd': str(root), 'disabled': False, 'alwaysAllow': []}
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
print('Prepared project-local .bob/mcp.json. This does not establish a verified Bob session.')
