"""Reuse the installed MySQL binary with isolated project data. No system service changes."""
import json, os, secrets, socket, subprocess, sys, time, shutil
from pathlib import Path
import MySQLdb
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parent.parent
STATE=ROOT/'.runtime';DATA=STATE/'mysql';CONFIG=STATE/'mysql-local.json'
MYSQL=Path(os.getenv('MYSQL_BINARY',r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'))
PORT=3307
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def running():
    try:
        with socket.create_connection(('127.0.0.1',PORT),timeout=1): return True
    except OSError: return False

def start():
    STATE.mkdir(exist_ok=True)
    if not MYSQL.exists(): raise RuntimeError(f'Installed MySQL binary not found: {MYSQL}')
    if not CONFIG.exists():
        if DATA.exists() and any(DATA.iterdir()): raise RuntimeError('Unconfigured data directory exists. Inspect it before retrying; nothing was deleted.')
        DATA.mkdir(exist_ok=True)
        result=subprocess.run([str(MYSQL),'--no-defaults','--initialize-insecure',f'--basedir={MYSQL.parent.parent}',f'--datadir={DATA}','--console'],capture_output=True,text=True,creationflags=FLAGS)
        (STATE/'mysql-initialize.log').write_text(result.stdout+result.stderr)
        if result.returncode: raise RuntimeError('MySQL initialization failed. See .runtime/mysql-initialize.log.')
        cfg={'port':PORT,'root_password':secrets.token_urlsafe(36),'app_password':secrets.token_urlsafe(36),'username':'areyouthere_local','configured':False}
        CONFIG.write_text(json.dumps(cfg),encoding='utf-8')
    cfg=json.loads(CONFIG.read_text())
    if not running():
        # The installed optional jemalloc DLL crashes this standalone process on
        # this Windows build. Use copies with MySQL's standard allocator fallback.
        # Never rename or modify DLLs in the system installation.
        local_bin=ROOT/'.tools'/'mysql'/'bin';local_bin.mkdir(parents=True,exist_ok=True)
        for source in [MYSQL,*MYSQL.parent.glob('*.dll')]:
            if source.name.lower()=='jemalloc.dll': continue
            target=local_bin/source.name
            if not target.exists():shutil.copy2(source,target)
        args=[str(local_bin/MYSQL.name),'--no-defaults',f'--basedir={MYSQL.parent.parent}',f'--datadir={DATA}',f'--port={PORT}','--bind-address=127.0.0.1','--mysqlx=0','--skip-log-bin',f'--pid-file={STATE / "mysql.pid"}',f'--log-error={STATE / "mysql.log"}']
        if not cfg['configured']:
            bootstrap=STATE/'mysql-bootstrap.sql'
            bootstrap.write_text(f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{cfg['root_password']}';\n",encoding='utf-8');args.append(f'--init-file={bootstrap}')
        proc=subprocess.Popen(args,cwd=STATE,creationflags=FLAGS,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        (STATE/'mysql-process.json').write_text(json.dumps({'pid':proc.pid}))
    for _ in range(40):
        try:
            conn=MySQLdb.connect(host='127.0.0.1',port=PORT,user='root',passwd=cfg['root_password'],connect_timeout=2);break
        except MySQLdb.Error: time.sleep(.5)
    else: raise RuntimeError('Project MySQL did not become ready. See .runtime/mysql.log.')
    if not cfg['configured']:
        with conn.cursor() as c:
            for db in ['areyouthere','test_areyouthere']: c.execute(f'CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
            c.execute("CREATE USER IF NOT EXISTS %s@'localhost' IDENTIFIED BY %s",(cfg['username'],cfg['app_password']))
            for db in ['areyouthere','test_areyouthere']: c.execute(f"GRANT ALL PRIVILEGES ON `{db}`.* TO %s@'localhost'",(cfg['username'],))
        cfg['configured']=True;CONFIG.write_text(json.dumps(cfg),encoding='utf-8')
        (STATE/'mysql-bootstrap.sql').unlink(missing_ok=True)
    conn.close()
    env=dict(dotenv_values(ROOT/'.env')) if (ROOT/'.env').exists() else {}
    env.update(MYSQL_HOST='127.0.0.1',MYSQL_PORT=str(PORT),MYSQL_DATABASE='areyouthere',MYSQL_USER=cfg['username'],MYSQL_PASSWORD=cfg['app_password'],LOCAL_MYSQL='1')
    env.setdefault('DJANGO_SECRET_KEY',secrets.token_urlsafe(48));env.setdefault('DEBUG','1');env.setdefault('REDIS_URL','redis://127.0.0.1:6379/0')
    (ROOT/'.env').write_text(''.join(f'{k}={v}\n' for k,v in env.items()),encoding='utf-8')
    print('Isolated MySQL ready at 127.0.0.1:3307. Existing MySQL80 service unchanged.')

def stop():
    if not CONFIG.exists() or not running():return
    cfg=json.loads(CONFIG.read_text());conn=MySQLdb.connect(host='127.0.0.1',port=PORT,user='root',passwd=cfg['root_password'],connect_timeout=3)
    try:conn.shutdown()
    finally:conn.close()

if __name__=='__main__':
    stop() if '--stop' in sys.argv else start()
