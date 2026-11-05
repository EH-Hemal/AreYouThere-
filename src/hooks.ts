import {useCallback,useEffect,useRef,useState} from 'react';
import {api,API} from './api';
import type {Room} from './types';
export function useRoom(id:number|null){
 const [room,setRoom]=useState<Room|null>(null),[error,setError]=useState(''),[connection,setConnection]=useState('connecting'),[offset,setOffset]=useState(0);
 const generation=useRef(0);
 const refresh=useCallback(async()=>{if(!id)return;const current=generation.current;try{const value=await api<Room>(`/sessions/${id}/`);if(current!==generation.current)return;setRoom(value);setOffset(new Date(value.server_time).getTime()-Date.now());setError('')}catch(e){if(current===generation.current){setError((e as Error).message);setConnection('reconnecting')}}},[id]);
 useEffect(()=>{generation.current++;setRoom(null);setError('');if(!id)return;let disposed=false,socket:WebSocket|null=null,retry:ReturnType<typeof setTimeout>,attempt=0;
   refresh();
   const beat=()=>api(`/sessions/${id}/heartbeat/`,{}).catch(()=>{});beat();
   const connect=async()=>{setConnection('connecting');try{const {ticket}=await api<{ticket:string}>(`/sessions/${id}/ticket/`,{});if(disposed)return;const origin=API||window.location.origin;socket=new WebSocket(`${origin.replace(/^http/,'ws')}/ws/sessions/${id}/?ticket=${encodeURIComponent(ticket)}`);socket.onopen=()=>{attempt=0;setConnection('connected');refresh()};socket.onmessage=()=>refresh();socket.onerror=()=>socket?.close();socket.onclose=()=>{if(disposed)return;setConnection('reconnecting');retry=setTimeout(connect,Math.min(30000,1000*2**attempt++))}}catch{if(!disposed){setConnection('reconnecting');retry=setTimeout(connect,5000)}}};connect();
   const poll=setInterval(refresh,8000),heartbeat=setInterval(beat,15000);const resync=()=>{beat();refresh()};
   const offline=()=>{setConnection('reconnecting');socket?.close()};
   const online=()=>{resync();if(socket?.readyState===WebSocket.OPEN)setConnection('connected')};
   window.addEventListener('offline',offline);window.addEventListener('online',online);window.addEventListener('focus',resync);
   return()=>{disposed=true;generation.current++;clearTimeout(retry);clearInterval(poll);clearInterval(heartbeat);socket?.close();window.removeEventListener('offline',offline);window.removeEventListener('online',online);window.removeEventListener('focus',resync)};
 },[id,refresh]);
 return {room,error,connection,refresh,setRoom,offset};
}
export function useNow(){const [now,setNow]=useState(Date.now());useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),500);return()=>clearInterval(timer)},[]);return now}
