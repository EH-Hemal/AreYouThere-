import os,subprocess,time,urllib.request,sys
from pathlib import Path
root=Path.cwd();py=root/'.venv/Scripts/python.exe';sys.path.insert(0,str(root/'scripts'))
from launcher import start,stop
stop()
subprocess.run([str(py),'scripts/prepare_browser_test.py'],check=True)
env=os.environ.copy();env['MYSQL_DATABASE']='test_areyouthere'
log=(root/'.runtime/browser-backend.log').open('w')
backend=subprocess.Popen([str(py),'backend/manage.py','runserver','127.0.0.1:8000','--noreload'],env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
dashboard=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1'],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for _ in range(40):
        try:
            urllib.request.urlopen('http://127.0.0.1:8000/api/health/',timeout=2)
            urllib.request.urlopen('http://127.0.0.1:5173/',timeout=2)
            break
        except Exception:time.sleep(.5)
    subprocess.run(['node','node_modules/playwright/cli.js','test',*sys.argv[1:]],check=True)
finally:
    backend.terminate();dashboard.terminate();backend.wait(timeout=10);dashboard.wait(timeout=10);log.close();start()
