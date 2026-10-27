"""Run only on the dedicated Ubuntu runner after installation; stdlib only.

Exercises real authenticated jobs. Never import the runner implementation here.
Expected outputs remain inside the runner service. Results are saved without keys.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def content_digest():
    root = Path(os.environ.get('RUNNER_CONTENT_ROOT', '/srv/fieldnote-runner/content'))
    problem = json.loads((root/'coding/backend_frequency_counts.json').read_text(encoding='utf-8-sig'))
    hidden = json.loads((root/'coding-private'/(problem['hidden_test_set']+'.json')).read_text(encoding='utf-8-sig'))
    return hashlib.sha256(json.dumps({'problem':problem,'hidden':hidden},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def request(method, path, body=None, authenticated=True):
    if method == 'POST' and path == '/jobs':
        body = {**body, 'content_digest': content_digest()}
    headers={'Content-Type':'application/json'}
    if authenticated:
        headers['Authorization']='Bearer '+os.environ['RUNNER_BEARER_TOKEN']
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=10) as response:
        raw=response.read()
        return json.loads(raw) if raw else None


def run_case(name,language,source,expected):
    job_id='acceptance-'+uuid.uuid4().hex
    started=time.monotonic()
    payload={'id':job_id,'language':language,'source':source,'problem_id':'backend_frequency_counts','mode':'submit'}
    try:
        result=request('POST','/jobs',payload)
        duplicate=request('POST','/jobs',payload)
        assert duplicate['id']==job_id,'Idempotent retry changed job ID'
        deadline=time.monotonic()+70
        while result['status'] in {'queued','running'}:
            if time.monotonic()>deadline:
                raise AssertionError('Job did not terminate within acceptance deadline')
            time.sleep(.2)
            result=request('GET','/jobs/'+job_id)
        kind=(result.get('result') or {}).get('kind',result['status'])
        assert kind==expected,f'Expected {expected}, observed {kind}'
        if expected in {'timeout','output_limit'}:
            execution=result['result']
            assert len(execution.get('public',[]))==1,'Suite continued after the first case budget breach'
            assert execution.get('hidden',{}).get('total',0)==0,'Hidden cases ran after a public case budget breach'
        return {'case':name,'passed':True,'observed':kind,'elapsed_seconds':time.monotonic()-started}
    except Exception as exc:
        return {'case':name,'passed':False,'error':str(exc),'elapsed_seconds':time.monotonic()-started}
    finally:
        try:
            request('DELETE','/jobs/'+job_id)
            try:
                request('GET','/jobs/'+job_id)
                raise AssertionError('Deleted job remained readable')
            except urllib.error.HTTPError as exc:
                if exc.code!=404:raise
        except urllib.error.HTTPError as exc:
            if exc.code!=404:raise


def cancellation_case():
    job_id='acceptance-'+uuid.uuid4().hex
    try:
        request('POST','/jobs',{'id':job_id,'language':'python','source':'while True: pass',
                              'problem_id':'backend_frequency_counts','mode':'run'})
        request('DELETE','/jobs/'+job_id)
        try:
            request('GET','/jobs/'+job_id)
        except urllib.error.HTTPError as exc:
            assert exc.code==404
        else:
            raise AssertionError('Cancelled job remained readable')
        return {'case':'cancel-active-job','passed':True,'observed':'deleted'}
    except Exception as exc:
        return {'case':'cancel-active-job','passed':False,'error':str(exc)}
    finally:
        try:request('DELETE','/jobs/'+job_id)
        except urllib.error.HTTPError as exc:
            if exc.code!=404:raise


if __name__=='__main__':
    if not sys.platform.startswith('linux') or not Path('/etc/os-release').exists():
        raise SystemExit('Run this acceptance script only on the dedicated Ubuntu runner PC.')
    if not os.getenv('RUNNER_BEARER_TOKEN'):
        raise SystemExit('Load RUNNER_BEARER_TOKEN from the protected runner environment; never pass it in a URL.')
    BASE=os.getenv('RUNNER_ACCEPTANCE_URL','http://127.0.0.1:9000').rstrip('/')
    health=request('GET','/health')
    if health.get('status')!='ready' or health.get('isolation')!='runsc':
        raise SystemExit('Runner is not ready with runsc; no candidate acceptance jobs were submitted.')
    try:
        request('GET','/health',authenticated=False)
        raise SystemExit('Unauthenticated health request unexpectedly succeeded')
    except urllib.error.HTTPError as exc:
        if exc.code!=401:raise
    correct_python='import sys\nfrom collections import Counter\na=sys.stdin.read().split()\nc=Counter(x.lower() for x in a[1:])\nfor k in sorted(c): print(k,c[k])\n'
    correct_cpp='#include <iostream>\n#include <map>\n#include <string>\n#include <cctype>\nint main(){int n;std::cin>>n;std::map<std::string,int> c;while(n--){std::string s;std::cin>>s;for(char &x:s)x=std::tolower(static_cast<unsigned char>(x));++c[s];}for(auto &[s,n]:c)std::cout<<s<<" "<<n<<"\\n";}\n'
    cases=[('python-correct','python',correct_python,'passed'),('cpp-correct','cpp',correct_cpp,'passed'),('wrong-answer','python','print("wrong")','wrong_answer'),('compile-error','cpp','int main( {','compile_error'),('runtime-error','python','raise RuntimeError("synthetic")','runtime_error'),('timeout','python','while True: pass','timeout'),('output-limit','python','while True: print("x"*4096,flush=True)','output_limit')]
    results=[run_case(*case) for case in cases]
    results.append(run_case('combined-stdout-stderr-limit','python',
        'import sys\nsys.stdout.write("x"*40000)\nsys.stdout.flush()\nsys.stderr.write("y"*40000)\nsys.stderr.flush()\n','output_limit'))
    network_probe='''import socket
from pathlib import Path
routes=Path('/proc/net/route').read_text().splitlines()[1:]
assert not any(len(row.split())>1 and row.split()[1]=='00000000' for row in routes), 'unexpected default network route'
probe=socket.socket()
probe.settimeout(0.2)
try:
    probe.connect(('192.0.2.1',80))
except OSError:
    pass
else:
    raise RuntimeError('unexpected external connection')
finally:
    probe.close()
'''
    process_probe='''import os
children=[]
limited=False
read_end,write_end=os.pipe()
try:
    for attempt in range(96):
        try:
            child=os.fork()
        except OSError:
            limited=True
            break
        if child==0:
            os.close(write_end)
            os.read(read_end,1)
            os._exit(0)
        children.append(child)
finally:
    os.close(write_end)
    os.close(read_end)
    for child in children:
        os.waitpid(child,0)
assert limited, 'process budget allowed 96 simultaneous child processes'
'''
    results.append(run_case('network-denial-probe','python',network_probe+correct_python,'passed'))
    results.append(run_case('finite-process-budget-probe','python',process_probe+correct_python,'passed'))
    results.append(cancellation_case())
    # A fresh known-good job proves the service remains usable after cancellation.
    results.append(run_case('after-cancellation','python',correct_python,'passed'))
    output=Path(os.getenv('RUNNER_ACCEPTANCE_OUTPUT','runner-acceptance-results.json'))
    output.write_text(json.dumps({'health':health,'real_execution':True,'checks':results,'limitations':['Network probes check default-route absence and one denied connection; they are not a complete network-isolation proof. The finite fork probe is behavioral, not independent cgroup/kernel verification. Memory/GPU/filesystem hardening and independent host review remain required.']},indent=2))
    print(json.dumps({'passed':sum(r['passed'] for r in results),'total':len(results),'output':str(output)}))
    sys.exit(0 if all(r['passed'] for r in results) else 1)
