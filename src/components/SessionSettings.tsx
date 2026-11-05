import {useState,useEffect} from 'react';
import {api} from '../api';
import {Button} from './ui/button';
import {Notice,Status} from './shared';
import type {Room,Question,Cell} from '../types';

export function SessionSettings(){
 const [mode,setMode]=useState('manual');
 return <fieldset><legend>Class timing</legend>
 <label>Class duration (seconds)<input name="class_duration" type="number" min={60} max={43200} defaultValue={3600} required/><span className="field-hint">Starts when you press Start session. The class ends automatically.</span></label>
 <label>Question delivery<select name="delivery_mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="manual">I will send questions during class</option><option value="fixed">At fixed intervals</option><option value="random">At random intervals</option></select></label>
 {mode==='fixed'&&<label>Time between questions (seconds)<input name="interval_seconds" type="number" min={10} max={3600} defaultValue={300} required/></label>}
 {mode==='random'&&<><label>Minimum interval (seconds)<input name="random_min" type="number" min={10} max={3600} defaultValue={180} required/></label><label>Maximum interval (seconds)<input name="random_max" type="number" min={10} max={3600} defaultValue={600} required/></label></>}
 {mode!=='manual'&&<p className="field-hint">Prepare questions in the queue. Delivery begins after the first interval; questions never overlap. Random mode varies the time, not the question order.</p>}
 <label>Default answer time (seconds)<input name="question_duration" type="number" min={10} max={3600} defaultValue={60} required/></label>
 <label>Ask about a missed question after (seconds)<input name="recovery_delay" type="number" min={0} max={3600} defaultValue={30} required/></label>
 <label>Time to explain the miss (seconds)<input name="recovery_duration" type="number" min={10} max={3600} defaultValue={60} required/><span className="field-hint">A reason is sent to the teacher for review. It does not count as an answer.</span></label>
 </fieldset>
}

export function ClassDirectory({onJoined}:{onJoined:(room:Room)=>void}){
 const [classes,setClasses]=useState<{id:number;title:string;teacher:string;status:string}[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false);
 useEffect(()=>{let alive=true;async function load(){try{const list=await api<typeof classes>('/classes/');if(alive){setClasses(list);setError('')}}catch(e){if(alive)setError((e as Error).message)}finally{if(alive)setLoading(false)}}load();const timer=setInterval(load,8000);return()=>{alive=false;clearInterval(timer)}},[]);
 return <section className="extension-history"><h2>Classes you can join</h2><Notice text={error}/>{loading?<p>Loading classes…</p>:!classes.length?<p className="muted small">No classes are open yet.</p>:classes.map(c=><article className="card" key={c.id} style={{marginBottom:12}}><div className="row-between"><h3>{c.title}</h3><Status status={c.status}/></div><p className="muted small">{c.teacher}</p><form onSubmit={async e=>{e.preventDefault();const data=new FormData(e.currentTarget);setBusy(true);try{onJoined(await api<Room>('/sessions/join/',{session_id:c.id,code:data.get('code')}))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}><label>Class code<input name="code" maxLength={6} minLength={6} required autoComplete="off"/></label><Button disabled={busy}>Join class</Button></form></article>)}</section>
}

export function RecoveryPrompt({sessionId,questions,cells,now,onDone}:{sessionId:number;questions:Question[];cells:Cell[];now:number;onDone:()=>void}){
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 const missed=questions.filter(q=>q.recovery_opens_at&&q.recovery_closes_at&&now>=Date.parse(q.recovery_opens_at)&&now<Date.parse(q.recovery_closes_at)&&cells.some(c=>c.question_id===q.id&&c.answer===null&&c.participation!=='not_eligible'&&!c.reason));
 return <>{missed.map(q=><section className="card" key={q.id} style={{marginBottom:16}} aria-label="Missed question recovery"><h2>What happened?</h2><p className="small">You missed: {q.prompt}</p><p className="field-hint">{Math.max(0,Math.ceil((Date.parse(q.recovery_closes_at!)-now)/1000))} seconds left to explain. Your teacher will review your reason.</p><Notice text={error}/><form onSubmit={async e=>{e.preventDefault();setBusy(true);try{await api(`/sessions/${sessionId}/questions/${q.id}/reason/`,Object.fromEntries(new FormData(e.currentTarget)));onDone();setError('')}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}><label>Why did you miss this question?<textarea name="text" required maxLength={1000} rows={3}/></label><Button disabled={busy}>Send reason</Button></form></section>)}</>
}
