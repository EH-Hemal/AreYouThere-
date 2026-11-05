import {useState} from 'react';
import {ArrowLeft,Copy,Download,Plus,Send} from 'lucide-react';
import {api,downloadCSV} from '../api';
import {useNow,useRoom} from '../hooks';
import type {Question} from '../types';
import {Badge,Empty,Loading,Modal,Notice,Status} from './shared';
import {Button} from './ui/button';
import {QuestionEditor} from './TeacherRoom';

export function TeacherExtension({id,onBack}:{id:number;onBack:()=>void}){
 const {room,error,connection,refresh,offset}=useRoom(id);
 const now=useNow();
 const [editing,setEditing]=useState<Question|true|null>(null);
 const [busy,setBusy]=useState(false);
 const [actionError,setActionError]=useState('');
 const [message,setMessage]=useState('');
 const [confirmEnd,setConfirmEnd]=useState(false);

 async function act(path:string,body?:unknown,method?:string){
  setBusy(true);setActionError('');setMessage('');
  try{await api(`/sessions/${id}/${path}`,body,method);await refresh()}
  catch(e){setActionError((e as Error).message)}finally{setBusy(false)}
 }
 async function copyCode(){
  if(!room)return;
  try{await navigator.clipboard.writeText(room.code);setMessage('Join code copied.')}catch{setMessage(`Join code: ${room.code}`)}
 }
 if(!room)return <><Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft size={15}/>All sessions</Button><Notice text={error}/>{error?<Button onClick={refresh}>Retry</Button>:<Loading/>}</>;

 const active=room.questions.find(q=>q.status==='open'&&q.deadline&&new Date(q.deadline).getTime()>now+offset);
 const latest=active||[...room.questions].reverse().find(q=>q.opened_at);
 const answered=latest?room.members.filter(m=>m.cells.some(c=>c.question_id===latest.id&&c.participation==='answered')).length:0;
 const eligible=latest?room.members.filter(m=>m.cells.some(c=>c.question_id===latest.id&&c.participation!=='not_eligible')).length:0;
 const pending=room.members.flatMap(m=>m.cells).filter(c=>c.reason?.status==='pending').length;
 return <div className="teacher-extension">
  <Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft size={15}/>All sessions</Button>
  <div className="teacher-extension-title"><div><span className="eyebrow">{room.course||'CLASSROOM'}</span><h1>{room.title}</h1></div><Status status={room.status}/></div>
  <Notice text={error||actionError}/><Notice text={message} success/>
  {connection!=='connected'&&<div className="sync-banner" role="status">Reconnecting. Checking for updates every 8 seconds.</div>}
  <button className="teacher-extension-code" onClick={copyCode} aria-label={`Copy join code ${room.code}`}><span>STUDENT JOIN CODE</span><strong>{room.code}</strong><Copy size={16}/></button>
  {room.ends_at&&<p className="field-hint">Class ends in {Math.max(0,Math.ceil((Date.parse(room.ends_at)-now-offset)/60))} minutes · {room.delivery_mode} questions</p>}<div className="teacher-extension-actions">
   {room.status==='lobby'&&<Button disabled={busy} onClick={()=>act('',{action:'start'})}>Start session</Button>}
   {room.status==='live'&&<Button variant="outline" disabled={busy} onClick={()=>setConfirmEnd(true)}>End session</Button>}
   <Button variant="outline" onClick={async()=>{try{await downloadCSV(id)}catch(e){setActionError((e as Error).message)}}}><Download size={15}/>Export report</Button>
  </div>
  <div className="teacher-extension-stats"><div><strong>{room.members.length}</strong><span>Students</span></div><div><strong>{answered}/{eligible}</strong><span>Latest answered</span></div><div><strong>{pending}</strong><span>Reasons to review</span></div></div>
  <section className="card teacher-extension-section"><div className="card-heading"><h2>{active?'Question live':'Questions'}</h2>{active&&<Badge tone="green">On air</Badge>}</div>
   {active&&<div className="teacher-extension-live"><strong>{active.prompt}</strong><p>{Math.max(0,Math.ceil((new Date(active.deadline!).getTime()-now-offset)/1000))} seconds left · {answered} of {eligible} answered</p><Button size="sm" variant="outline" disabled={busy} onClick={()=>act(`questions/${active.id}/`,{action:'close'})}>Close question</Button></div>}
   {room.status!=='ended'&&<Button className="full" onClick={()=>setEditing(true)}><Plus size={15}/>Create question</Button>}
   {room.questions.length===0?<p className="muted small">Create a multiple-choice or short-answer question.</p>:<div className="teacher-extension-questions">{room.questions.map((q,i)=><article key={q.id}><div className="row-between"><span className="small">Question {i+1}</span><Status status={q.status}/></div><strong>{q.prompt}</strong><p className="field-hint">{q.kind==='mcq'?'Multiple choice':'Short answer'} · {q.duration}s{q.scheduled_at?` · ${new Date(q.scheduled_at).toLocaleString()}`:''}</p>{q.schedule_error&&<Notice text={q.schedule_error}/>}{['draft','scheduled'].includes(q.status)&&room.status!=='ended'&&<div className="teacher-extension-question-actions"><Button size="sm" disabled={busy||!!active||room.status!=='live'} onClick={()=>act(`questions/${q.id}/`,{action:'open'})}><Send size={13}/>Send now</Button><Button size="sm" variant="outline" onClick={()=>setEditing(q)}>Edit</Button><Button size="sm" variant="ghost" disabled={busy} onClick={()=>act(`questions/${q.id}/`,undefined,'DELETE')}>Delete</Button></div>}</article>)}</div>}
  </section>
  <section className="card teacher-extension-section"><div className="card-heading"><h2>Live participation</h2><Badge>{room.members.length}</Badge></div>{room.members.length===0?<Empty title="Waiting for students" detail={`Share code ${room.code} to invite your class.`}/>:<div className="teacher-extension-students">{room.members.map(m=>{const cell=m.cells.find(c=>c.question_id===latest?.id);return <article key={m.id}><div className="row-between"><div><strong>{m.name}</strong><small>{m.connection==='connected'?'Connected':'Offline'} · {m.answered}/{m.eligible} answered</small></div>{cell?<Status status={cell.participation}/>:<span className="muted small">No question</span>}</div>{cell?.answer!==null&&cell?.answer!==undefined&&<p className="small">Answer: {latest?.kind==='mcq'?latest.options[Number(cell.answer)]:cell.answer}{cell.correct!==null?` · ${cell.correct?'Correct':'Incorrect'}`:''}</p>}{latest?.kind==='short'&&cell?.response_id&&cell.correct===null&&<div className="teacher-extension-question-actions"><Button size="sm" variant="outline" disabled={busy} onClick={()=>act(`responses/${cell.response_id}/grade/`,{correct:true})}>Mark correct</Button><Button size="sm" variant="outline" disabled={busy} onClick={()=>act(`responses/${cell.response_id}/grade/`,{correct:false})}>Mark incorrect</Button></div>}</article>})}</div>}</section>
  <section className="card teacher-extension-section"><div className="card-heading"><h2>Missed-response reasons</h2><Badge tone={pending?'amber':'neutral'}>{pending}</Badge></div>{room.members.flatMap(m=>m.cells.filter(c=>c.reason).map(c=><article className="teacher-extension-reason" key={c.reason!.id}><div className="row-between"><strong>{m.name}</strong><Status status={c.reason!.status}/></div><p className="small muted">{room.questions.find(q=>q.id===c.question_id)?.prompt}</p><p>{c.reason!.text}</p>{c.reason!.review_note&&<p className="field-hint">Review note: {c.reason!.review_note}</p>}{c.reason!.status==='pending'&&<form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);act(`reasons/${c.reason!.id}/review/`,{status:data.get('decision'),note:data.get('note')})}}><label>Review note (optional)<input name="note" maxLength={1000}/></label><label>Decision<select name="decision"><option value="accepted">Excuse this miss</option><option value="rejected">Reject reason</option></select></label><Button disabled={busy} size="sm">Save review</Button></form>}</article>))}{!room.members.some(m=>m.cells.some(c=>c.reason))&&<p className="muted small">Student explanations will appear here.</p>}</section>
  {editing&&<QuestionEditor room={room} question={editing===true?undefined:editing} onSaved={refresh} onClose={()=>setEditing(null)}/>}
  {confirmEnd&&<Modal title="End this session?" onClose={()=>setConfirmEnd(false)}><p>Open questions will close immediately.</p><div className="modal-actions"><Button variant="outline" onClick={()=>setConfirmEnd(false)}>Keep teaching</Button><Button variant="destructive" disabled={busy} onClick={()=>{setConfirmEnd(false);act('',{action:'end'})}}>End session</Button></div></Modal>}
 </div>
}
