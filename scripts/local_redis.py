"""Run the verified, project-local Memurai Developer runtime on loopback."""
import os,subprocess,socket,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
STATE=ROOT/'.runtime'
def ready():
    try:
        import redis
        return redis.Redis(host='127.0.0.1',port=6379,socket_timeout=1).ping()
    except Exception:return False
def start():
    if ready():print('Redis-compatible service already available.');return
    exe=ROOT/'.tools'/'memurai'/'memurai.exe'
    if not exe.exists():raise RuntimeError('Project-local Memurai is not installed. Run Setup.cmd.')
    data=STATE/'redis';data.mkdir(parents=True,exist_ok=True)
    conf=STATE/'memurai.conf'
    conf.write_text(f'bind 127.0.0.1\nprotected-mode yes\nport 6379\nappendonly yes\ndir "{data.as_posix()}"\nlogfile "{(STATE/"redis.log").as_posix()}"\n',encoding='utf-8')
    p=subprocess.Popen([str(exe),str(conf)],cwd=STATE,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (STATE/'redis-process.json').write_text(json.dumps({'pid':p.pid}))
    for _ in range(30):
        if ready():print('Project-local Redis delivery ready (Memurai Developer 4.1.2).');return
        time.sleep(.5)
    raise RuntimeError('Redis did not become ready. See .runtime/redis.log.')
if __name__=='__main__':start()
