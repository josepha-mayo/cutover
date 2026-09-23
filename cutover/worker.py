"""One bounded rehearsal per process; JSON input and output only."""
import json
import sys
from .engine import rehearse

request = json.load(sys.stdin)
print(json.dumps(rehearse(request['case'], request['plan']), ensure_ascii=True))
