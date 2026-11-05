import type {User} from './types';
const extension=typeof chrome!=='undefined' && !!chrome.runtime?.id;
export const API=extension?(import.meta.env.VITE_API_ORIGIN||'http://127.0.0.1:8000'):(import.meta.env.VITE_API_ORIGIN||'');
let token=extension?'':sessionStorage.getItem('ayt-token')||'';
export async function initializeAuth(){if(extension){const data=await chrome.storage.local.get('token');token=data.token||''}}
export function hasToken(){return !!token}
export async function saveToken(value:string){token=value;if(extension)await chrome.storage.local.set({token:value});else if(value)sessionStorage.setItem('ayt-token',value);else sessionStorage.removeItem('ayt-token')}
function message(data:unknown):string{if(typeof data==='string')return data;if(Array.isArray(data))return data.map(message).join(' ');if(data&&typeof data==='object')return Object.values(data).map(message).join(' ');return 'The request could not be completed.'}
export async function api<T>(path:string,body?:unknown,method?:string):Promise<T>{
  const response=await fetch(`${API}/api${path}`,{method:method||(body===undefined?'GET':'POST'),headers:{'Content-Type':'application/json',...(token?{Authorization:`Token ${token}`}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){let data:unknown;try{data=await response.json()}catch{data='Service unavailable. Please try again.'}if(response.status===401)window.dispatchEvent(new Event('ayt-unauthorized'));throw new Error(message(data))}
  const result=await response.json() as T;
  if(extension&&body!==undefined)chrome.runtime.sendMessage({type:'sync'}).catch(()=>{});
  return result;
}
export async function downloadCSV(id:number){const r=await fetch(`${API}/api/sessions/${id}/export/`,{headers:{Authorization:`Token ${token}`}});if(!r.ok)throw new Error('Could not export this report.');const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`areyouthere-session-${id}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
export type AuthResult={token:string;user:User};
