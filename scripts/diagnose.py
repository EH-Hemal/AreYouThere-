"""Read-only local diagnostics, without environment values or passwords."""
import os,psutil
from pathlib import Path
ROOT=str(Path(__file__).resolve().parent.parent).lower()
print('Available memory MB:',round(psutil.virtual_memory().available/1048576))
for p in psutil.process_iter(['pid','name','cmdline','cwd']):
    try:
        command=' '.join(p.info['cmdline'] or []);cwd=p.info['cwd'] or ''
        if p.info['name'].lower() in ['node.exe','python.exe','mysqld.exe'] and (ROOT in command.lower() or ROOT in cwd.lower()):
            print(p.pid,p.info['name'],round(p.memory_info().rss/1048576),'MB',command[:180])
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
