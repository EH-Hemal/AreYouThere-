from pathlib import Path
def edit(path,old,new):
 p=Path(path);s=p.read_text(encoding='utf-8');assert old in s,path;p.write_text(s.replace(old,new),encoding='utf-8')
edit('src/App.tsx',"import {TeacherRoom}","import {SessionSettings,ClassDirectory} from './components/SessionSettings';\nimport {TeacherRoom}")
edit('src/App.tsx','<form onSubmit={newSession}>','<form onSubmit={newSession}><SessionSettings/>')
edit('src/App.tsx','<JoinForm onJoined={r=>open(r.id)}/>','<ClassDirectory onJoined={r=>open(r.id)}/><JoinForm onJoined={r=>open(r.id)}/>')
edit('src/types.ts','export type Question={','export type Question={recovery_opens_at:string|null;recovery_closes_at:string|null;')
edit('src/types.ts','export type Room={','export type Room={class_duration:number;delivery_mode:string;question_duration:number;recovery_delay:number;recovery_duration:number;ends_at:string|null;next_question_at:string|null;')
edit('src/components/TeacherRoom.tsx','question?.duration||60','question?.duration||room.question_duration||60')
edit('src/components/Student.tsx',"import {useState", "import {RecoveryPrompt} from './SessionSettings';\nimport {useState")
edit('src/components/Student.tsx','<div className="student-columns">','<RecoveryPrompt sessionId={id} questions={room.questions} cells={member?.cells||[]} now={now+offset} onDone={refresh}/><div className="student-columns">')
edit('src/components/Student.tsx',"c.participation==='missed'&&<Button", "c.participation==='missed'&&(!q.recovery_opens_at||(now+offset>=Date.parse(q.recovery_opens_at)&&now+offset<Date.parse(q.recovery_closes_at!)))&&<Button")
edit('src/components/TeacherExtension.tsx','<div className="teacher-extension-actions">','{room.ends_at&&<p className="field-hint">Class ends in {Math.max(0,Math.ceil((Date.parse(room.ends_at)-now-offset)/60))} minutes · {room.delivery_mode} questions</p>}<div className="teacher-extension-actions">')
