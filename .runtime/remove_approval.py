from pathlib import Path

def edit(path, old, new):
    file=Path(path);text=file.read_text(encoding='utf-8')
    if old not in text:raise RuntimeError(f'Expected source not found in {path}: {old[:80]}')
    file.write_text(text.replace(old,new),encoding='utf-8')

edit('backend/config/urls.py',"path('api/approvals/',v.approvals),",'')
for path in ['backend/core/management/commands/bootstrap_admin.py','backend/core/management/commands/seed_demo.py','scripts/prepare_browser_test.py','backend/core/tests.py']:
    edit(path,',approved=True','')
edit('src/types.ts','approved:boolean;','')
edit('src/App.tsx',",[approvals,setApprovals]=useState<User[]>([])",'')
edit('src/App.tsx',"if(user){loadSessions();if(user.admin)api<User[]>('/approvals/').then(setApprovals).catch(e=>setError(e.message))}","if(user)loadSessions()")
edit('src/App.tsx',",...(user.admin?[{id:'approvals',icon:ShieldCheck,label:'Teacher approvals'}]:[])",'')
edit('src/App.tsx',"page==='approvals'?'Approvals':",'')
path=Path('src/App.tsx');text=path.read_text(encoding='utf-8')
start=text.index("{teacher&&!user.approved?")
end=text.index(':roomId?',start)
text=text[:start]+'{roomId?'+text[end+len(':roomId?'):]
start=text.index(":page==='approvals'&&user.admin?")
end=text.index(":page==='guide'?",start)
text=text[:start]+text[end:]
text=text.replace("<dt>Approval</dt><dd>{user.approved?'Approved':'Pending'}</dd>",'')
path.write_text(text,encoding='utf-8')
edit('src/components/Auth.tsx',"{role==='teacher'&&<p className=\"field-hint\">An administrator will review your teacher account before you can host a class.</p>}",'')
