import {useEffect,useRef,type ReactNode} from 'react';
import {AlertCircle,CheckCircle2,Radio,ShieldCheck,X} from 'lucide-react';
import {Button} from './ui/button';
export function Brand(){return <span className="brand"><span className="brand-icon"><Radio size={21}/></span>AreYouThere<span className="brand-question">?</span></span>}
export function Badge({children,tone='neutral'}:{children:ReactNode;tone?:string}){return <span className={`badge badge-${tone}`}>{children}</span>}
export function Status({status}:{status:string}){return <Badge tone={status==='live'||status==='connected'||status==='answered'||status==='accepted'?'green':status==='missed'||status==='rejected'?'red':status==='scheduled'||status==='pending'||status==='awaiting'?'amber':'neutral'}><span className="status-dot"/>{status.replaceAll('_',' ').replace('accepted','excused')}</Badge>}
export function Notice({text,success=false}:{text:string;success?:boolean}){if(!text)return null;return <div role={success?'status':'alert'} className={`notice ${success?'notice-success':''}`}>{success?<CheckCircle2 size={18}/>:<AlertCircle size={18}/>}<span>{text}</span></div>}
export function Privacy(){return <div className="privacy"><ShieldCheck size={16}/><span>Camera-free. Only your class responses are recorded.</span></div>}
export function Modal({title,children,onClose}:{title:string;children:ReactNode;onClose:()=>void}){const ref=useRef<HTMLDialogElement>(null);useEffect(()=>{ref.current?.showModal()},[]);return <dialog ref={ref} className="modal" onCancel={onClose}><div className="modal-head"><h2>{title}</h2><Button variant="ghost" size="icon" onClick={onClose} aria-label="Close dialog"><X size={20}/></Button></div>{children}</dialog>}
export function Empty({title,detail,action}:{title:string;detail:string;action?:ReactNode}){return <div className="empty"><span className="empty-icon"><Radio size={27}/></span><h3>{title}</h3><p>{detail}</p>{action}</div>}
export function Loading(){return <div className="loading" role="status"><span className="spinner"/>Loading your workspace…</div>}
export const formatDate=(v:string)=>new Date(v).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
