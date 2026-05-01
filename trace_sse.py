import requests
import json

import requests
import json

url = 'http://localhost:8000/agents/architect/runs'
data = {'message': 'hello', 'stream': 'true', 'session_id': 'trace-full-' + __import__('time').strftime('%H%M%S')}
print(f"POST {url}")
resp = requests.post(url, data=data, stream=True, timeout=120)
print(f"Status: {resp.status_code}")

for line in resp.iter_lines():
    if line:
        d = line.decode('utf-8')
        if d.startswith('data:'):
            try:
                p = json.loads(d[5:].strip())
                ev = p.get('event', 'unknown')
                if ev in ('FollowupsCompleted', 'RunCompleted', 'RunContentCompleted'):
                    print(f"\n=== {ev} ===")
                    print(json.dumps({k: v for k, v in p.items() if k != 'content' or len(str(v)) < 100}, indent=2))
            except Exception as e:
                print(f"  PARSE ERROR: {e} | raw={d[:100]}")

print("\nstream done")
data = {'message': 'hello', 'stream': 'true', 'session_id': 'trace-test-xyz2'}
print(f"POST {url}")
resp = requests.post(url, data=data, stream=True, timeout=120)
print(f"Status: {resp.status_code}")

for line in resp.iter_lines():
    if line:
        d = line.decode('utf-8')
        if d.startswith('data:'):
            try:
                p = json.loads(d[5:].strip())
                ev = p.get('event', 'unknown')
                print(f"  event={ev}")
            except Exception as e:
                print(f"  PARSE ERROR: {e} | raw={d[:100]}")
        elif d.startswith('event:'):
            print(f"  SSE event-line: {d}")

print("stream done")
