"""One bounded rehearsal per process; JSON input and output only."""
import json
import sqlite3
import sys
from .engine import digest, rehearse, validate_contract, validate_old_contract_behavior

try:
    request = json.load(sys.stdin)
    if request.get('operation') == 'validate_contract':
        contract = validate_contract(request['contract'])
        validate_old_contract_behavior(contract)
        result = {
            'status': 'valid', 'project': contract['project'], 'summary': contract['summary'],
            'contract_hash': digest(contract), 'seed_count': len(contract['seed']),
            'payload_count': len(contract['payloads']),
        }
    else:
        result = rehearse(request['case'], request['plan'], request.get('contract'))
    print(json.dumps(result, ensure_ascii=True))
except (ValueError, sqlite3.Error, KeyError, TypeError) as exc:
    print(json.dumps({'error': str(exc)[:400]}, ensure_ascii=True))
    sys.exit(2)
