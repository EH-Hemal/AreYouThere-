"""Local-only credential dialog. The administrator password is never saved."""
import os, secrets, sys, tkinter as tk
from pathlib import Path
from tkinter import messagebox
import MySQLdb
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
window = tk.Tk()
window.title('AreYouThere? · Connect your MySQL')
window.geometry('520x420')
window.configure(padx=28,pady=24)
tk.Label(window,text='Connect your existing MySQL',font=('Segoe UI',18,'bold')).pack(anchor='w')
tk.Label(window,text='MySQL 8.0.44 is running on port 3306.\nEnter a local MySQL administrator login. Its password\nis used once and never stored. Only areyouthere and\ntest_areyouthere will be created, with a dedicated app user.',justify='left').pack(anchor='w',pady=14)
entries = {}
for label, default, secret in [('Host','127.0.0.1',False),('Username','root',False),('Password','',True)]:
    tk.Label(window,text=label).pack(anchor='w')
    field=tk.Entry(window,show='*' if secret else '',width=60)
    field.insert(0,default); field.pack(anchor='w',pady=(0,8)); entries[label]=field

def connect():
    try:
        host=entries['Host'].get().strip()
        conn=MySQLdb.connect(host=host,user=entries['Username'].get().strip(),passwd=entries['Password'].get(),port=3306,connect_timeout=5)
        cursor=conn.cursor()
        cursor.execute('SELECT VERSION()'); version=cursor.fetchone()[0]
        password=secrets.token_urlsafe(32)
        for db in ['areyouthere','test_areyouthere']:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        # A random project-specific username avoids changing any existing account.
        username='ayt_'+secrets.token_hex(5)
        cursor.execute('CREATE USER %s@\'localhost\' IDENTIFIED BY %s',(username,password))
        for db in ['areyouthere','test_areyouthere']:
            cursor.execute(f'GRANT ALL PRIVILEGES ON `{db}`.* TO %s@\'localhost\'',(username,))
        conn.close()
        env=dict(dotenv_values(ROOT/'.env')) if (ROOT/'.env').exists() else {}
        env.update(MYSQL_HOST=host,MYSQL_PORT='3306',MYSQL_DATABASE='areyouthere',MYSQL_USER=username,MYSQL_PASSWORD=password)
        env.setdefault('DJANGO_SECRET_KEY',secrets.token_urlsafe(48));env.setdefault('DEBUG','1');env.setdefault('REDIS_URL','redis://127.0.0.1:6379/0')
        (ROOT/'.env').write_text(''.join(f'{k}={v}\n' for k,v in env.items()),encoding='utf-8')
        (ROOT/'.runtime').mkdir(exist_ok=True)
        (ROOT/'.runtime'/'database-ready').write_text(version,encoding='utf-8')
        entries['Password'].delete(0,'end')
        messagebox.showinfo('Connected',f'MySQL {version} is connected. Local project configuration saved.');window.destroy()
    except Exception as exc:
        messagebox.showerror('Connection failed',str(exc))

tk.Button(window,text='Connect and configure this project',command=connect,pady=7).pack(anchor='w',pady=10)
window.mainloop()
