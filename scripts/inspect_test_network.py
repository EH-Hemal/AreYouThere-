import json,zipfile
from pathlib import Path
for trace in Path('test-results').rglob('trace.zip'):
    with zipfile.ZipFile(trace) as z:
        for name in z.namelist():
            if not name.endswith('network'):continue
            for line in z.read(name).decode().splitlines():
                d=json.loads(line).get('snapshot',{});u=d.get('request',{}).get('url','');r=d.get('response',{})
                if '/api/' in u:print(u,r.get('status'),d.get('_failureText'),[(x['name'],x['value']) for x in r.get('headers',[]) if x['name'].lower().startswith('access-control')])
