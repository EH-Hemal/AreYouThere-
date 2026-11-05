"""Double-click setup entry point; reuse installed tools and configure local services."""
import hashlib,os,shutil,subprocess,sys,urllib.request,venv
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
os.chdir(ROOT)
PY=ROOT/'.venv'/'Scripts'/'python.exe'
def run(args,**kw):subprocess.run([str(a) for a in args],check=True,**kw)
def memurai():
    target=ROOT/'.tools'/'memurai';exe=target/'memurai.exe'
    if exe.exists():return
    tools=ROOT/'.tools';tools.mkdir(exist_ok=True)
    installer=tools/'Memurai.msi'
    if not installer.exists():urllib.request.urlretrieve('https://dist.memurai.com/releases/Memurai-Developer/4.1.2/Memurai-Developer-v4.1.2.msi',installer)
    if hashlib.sha256(installer.read_bytes()).hexdigest()!='11d009c8e93912e1899b5263d0e7d78907903913e1672b30020612ada6d27446':raise RuntimeError('Memurai download checksum mismatch. Nothing was executed.')
    target.mkdir(exist_ok=True)
    # Read the embedded cabinet with Windows' MSI API, then extract with expand.
    script=r"""$installer=New-Object -ComObject WindowsInstaller.Installer
$db=$installer.OpenDatabase((Join-Path (Get-Location) '.tools\Memurai.msi'),0)
$view=$db.OpenView('SELECT `Data` FROM `_Streams` WHERE `Name`=''cab1.cab''')
$view.Execute(); $record=$view.Fetch(); $binary=$record.ReadStream(1,$record.DataSize(1),1)
[IO.File]::WriteAllBytes((Join-Path (Get-Location) '.tools\memurai.cab'),[Text.Encoding]::GetEncoding(28591).GetBytes($binary))
expand.exe '.tools\memurai.cab' -F:* '.tools\memurai'
"""
    run(['powershell.exe','-NoProfile','-Command',script])
    for source,name in [('file_memurai.exe','memurai.exe'),('file_memurai_services.dll','memurai-services.dll'),('libcrypto_3_x64.dll','libcrypto-3-x64.dll'),('libssl_3_x64.dll','libssl-3-x64.dll')]:shutil.copy2(target/source,target/name)
def main():
    if os.name!='nt':raise RuntimeError('This automatic desktop setup targets Windows. See DEPLOYMENT.md for Linux.')
    if not shutil.which('node') or not shutil.which('npm.cmd'):raise RuntimeError('Node.js 22+ is required. Install the official Node LTS distribution.')
    if not PY.exists():venv.EnvBuilder(with_pip=True).create(ROOT/'.venv')
    run([PY,'-m','pip','install','-r','backend/requirements.lock.txt'])
    run(['npm.cmd','ci'],shell=True)
    memurai()
    run([PY,'scripts/local_mysql.py']);run([PY,'scripts/local_redis.py'])
    run([PY,'backend/manage.py','migrate','--noinput']);run([PY,'backend/manage.py','bootstrap_admin'])
    run(['npm.cmd','run','build'],shell=True)
    print('Setup complete. Double-click Launch.cmd. Administrator login is in .runtime/admin-login.txt.')
if __name__=='__main__':
    try:main()
    except Exception as exc:print(f'SETUP BLOCKED: {exc}');sys.exit(1)
