"""Own and supervise the local backend, scheduler and dashboard processes."""
import json,os,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parent.parent;STATE=ROOT/'.runtime';PY=ROOT/'.venv'/'Scripts'/'python.exe'
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
def available(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return r.status==200
    except Exception:return False
def start():
    os.chdir(ROOT);STATE.mkdir(exist_ok=True)
    env=dict(dotenv_values(ROOT/'.env')) if (ROOT/'.env').exists() else {}
    if env.get('LOCAL_MYSQL')=='1' or not env:
        from local_mysql import start as mysql_start
        mysql_start()
    from local_redis import start as redis_start
    redis_start()
    for command in [('migrate','--noinput'),('bootstrap_admin',)]:
        subprocess.run([str(PY),'backend/manage.py',*command],check=True,creationflags=FLAGS)
    if (STATE/'processes.json').exists():
        if available('http://127.0.0.1:8000/api/health/') and available('http://127.0.0.1:5173/'):
            print('Local workspace is already running.');return
        stop()
    processes=[]
    commands=[('backend',[str(PY),'-m','daphne','-b','127.0.0.1','-p','8000','config.asgi:application'],ROOT/'backend'),('scheduler',[str(PY),'backend/manage.py','run_scheduler'],ROOT),('dashboard',['node',str(ROOT/'node_modules'/'vite'/'bin'/'vite.js'),'--host','127.0.0.1','--port','5173','--strictPort'],ROOT)]
    for name,args,cwd in commands:
        log=(STATE/f'{name}.log').open('a',encoding='utf-8')
        clean_env=os.environ.copy();clean_env.pop('MYSQL_DATABASE',None)
        proc=subprocess.Popen(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,creationflags=FLAGS,env=clean_env)
        processes.append({'name':name,'pid':proc.pid,'command':args});log.close()
    (STATE/'processes.json').write_text(json.dumps(processes,indent=2))
    for _ in range(40):
        if available('http://127.0.0.1:8000/api/health/') and available('http://127.0.0.1:5173/'):print('AreYouThere? is ready at http://127.0.0.1:5173');return
        time.sleep(.5)
    raise RuntimeError('Some services did not become ready. See .runtime/backend.log, scheduler.log, and dashboard.log.')
def stop():
    if not (STATE/'processes.json').exists():return
    stopping=[]
    for p in json.loads((STATE/'processes.json').read_text()):
        # Verify the process command line belongs to this exact project before stopping it.
        try:
            import psutil
            process=psutil.Process(p['pid']);cmd=' '.join(process.cmdline())
            if str(ROOT).lower() in cmd.lower() or (p['name']=='backend' and process.cwd().lower()==str(ROOT/'backend').lower()):process.terminate();stopping.append(process)
        except (ImportError,ProcessLookupError):pass
        except Exception:pass
    if stopping:
        _,alive=psutil.wait_procs(stopping,timeout=8)
        for process in alive:process.kill()
    (STATE/'processes.json').unlink(missing_ok=True)
def gui():
    import tkinter as tk
    from tkinter import messagebox
    import threading
    window=tk.Tk();window.title('AreYouThere? · Local workspace');window.geometry('490x270');window.configure(padx=28,pady=24)
    tk.Label(window,text='AreYouThere?',font=('Segoe UI',23,'bold'),fg='#13795f').pack(anchor='w')
    status=tk.StringVar(value='Starting your local classroom…')
    tk.Label(window,textvariable=status,wraplength=420,justify='left').pack(anchor='w',pady=18)
    def launch():
        try:start();window.after(0,lambda:status.set('Ready. Your MySQL data and credentials stay on this computer.'));webbrowser.open('http://127.0.0.1:5173/')
        except Exception as exc:
            message=str(exc);window.after(0,lambda:status.set(message))
    tk.Button(window,text='Open dashboard',command=lambda:webbrowser.open('http://127.0.0.1:5173/')).pack(anchor='w',pady=5)
    tk.Button(window,text='Show local administrator login',command=lambda:os.startfile(STATE/'admin-login.txt')).pack(anchor='w',pady=5)
    threading.Thread(target=launch,daemon=True).start();window.mainloop()
if __name__=='__main__':
    if '--stop' in sys.argv:stop()
    elif '--start' in sys.argv:start()
    else:gui()
