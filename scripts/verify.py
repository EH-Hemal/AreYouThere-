"""Run all checks against real local services, restoring normal launch afterward."""
import os,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;os.chdir(ROOT)
PY=ROOT/'.venv'/'Scripts'/'python.exe'
def run(args,**kwargs):subprocess.run([str(x) for x in args],check=True,**kwargs)
def wait(url):
    for _ in range(30):
        try:
            with urllib.request.urlopen(url,timeout=2) as response:
                if response.status==200:return
        except Exception:time.sleep(.5)
    raise RuntimeError(f'Service did not become ready: {url}')
def main():
    from launcher import stop
    stop();run([PY,'scripts/local_mysql.py']);run([PY,'scripts/local_redis.py'])
    run([PY,'backend/manage.py','test','core','--keepdb','--noinput'])
    run(['npm.cmd','run','build'],shell=True)
    run([PY,'scripts/prepare_browser_test.py'])
    env=os.environ.copy();env['MYSQL_DATABASE']='test_areyouthere'
    log=(ROOT/'.runtime'/'browser-backend.log').open('w')
    backend=subprocess.Popen([str(PY),'backend/manage.py','runserver','127.0.0.1:8000','--noreload'],env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    dashboard=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1'],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        wait('http://127.0.0.1:8000/api/health/');wait('http://127.0.0.1:5173/')
        run(['node','node_modules/playwright/cli.js','test'])
    finally:
        backend.terminate();dashboard.terminate();backend.wait(timeout=10);dashboard.wait(timeout=10);log.close()
    run([PY,'scripts/launcher.py','--start'])
if __name__=='__main__':
    try:main()
    except Exception as exc:print(f'VERIFICATION FAILED: {exc}');sys.exit(1)
