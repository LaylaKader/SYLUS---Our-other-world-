import React, { useEffect, useRef, useState } from "react";
import { PhoneOff, Mic, Volume2, ShieldCheck } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getCallPreferences } from "../endpoints/call-preferences_GET.schema";
import { postCallPreferences } from "../endpoints/call-preferences_POST.schema";
import styles from "./VoiceCallPanel.module.css";
type Message = { id: number; role: string; text: string | null; createdAt: Date | string };
type Props = { messages: Message[]; onSend: (text: string) => void; onClose: () => void };
export default function VoiceCallPanel({ messages, onSend, onClose }: Props) {
  const qc = useQueryClient();
  const pref = useQuery({ queryKey: ["sylus-call-preferences"], queryFn: getCallPreferences });
  const [active,setActive]=useState(false),[listening,setListening]=useState(false),[notice,setNotice]=useState("Voice stays in this browser session."),[spontaneous,setSpontaneous]=useState(true);
  const recognition=useRef<any>(null),activeRef=useRef(false),lastSpoken=useRef<number|null>(null);
  useEffect(()=>{if(pref.data?.preferences)setSpontaneous(pref.data.preferences.spontaneousCallsEnabled)},[pref.data]);
  useEffect(()=>{
    const last=[...messages].reverse().find(m=>m.role==="model"&&m.text?.trim());
    if(!activeRef.current||!last||lastSpoken.current===last.id)return;
    lastSpoken.current=last.id;
    const synth=window.speechSynthesis;if(!synth)return;
    synth.cancel();const utterance=new SpeechSynthesisUtterance(last.text||"");
    const voices=synth.getVoices();const chosen=voices.find(v=>/male|daniel|david|alex|george|guy|james|aaron/i.test(v.name))||voices[0];
    if(chosen)utterance.voice=chosen;utterance.pitch=0.82;utterance.rate=0.91;
    utterance.onend=()=>{if(activeRef.current)startListening()};synth.speak(utterance);
  },[messages]);
  useEffect(()=>()=>{activeRef.current=false;recognition.current?.stop?.();window.speechSynthesis?.cancel()},[]);
  function startListening(){
    const SR=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;
    if(!SR){setNotice("Speech recognition is unavailable in this browser. Use text chat instead.");return}
    try{recognition.current?.stop?.();const rec=new SR();recognition.current=rec;rec.lang="en-US";rec.continuous=false;rec.interimResults=false;
      rec.onstart=()=>setListening(true);rec.onend=()=>setListening(false);
      rec.onerror=(e:any)=>setNotice(e?.error==="not-allowed"?"Microphone permission was denied.":"I couldn't hear that. Try again.");
      rec.onresult=(e:any)=>{const text=e.results?.[0]?.[0]?.transcript?.trim();if(text){setNotice("You: "+text);onSend(text)}};
      rec.start();
    }catch{setNotice("The microphone could not start. Check browser permission.")}
  }
  function begin(){activeRef.current=true;setActive(true);setNotice("Listening. Speak naturally.");startListening()}
  function end(){activeRef.current=false;setActive(false);setListening(false);recognition.current?.stop?.();window.speechSynthesis?.cancel();setNotice("Voice session ended.")}
  async function toggle(value:boolean){setSpontaneous(value);try{await postCallPreferences({spontaneousCallsEnabled:value});await qc.invalidateQueries({queryKey:["sylus-call-preferences"]})}catch{setSpontaneous(!value);setNotice("Could not save your calling preference.")}}
  const restriction=pref.data?.preferences;
  return <div className={styles.backdrop} role="dialog" aria-modal="true" aria-label="Voice conversation with Sylus"><section className={styles.panel}>
    <button className={styles.close} onClick={onClose} aria-label="Close">×</button><div className={styles.sig}>✦</div><p className={styles.eyebrow}>PRIVATE VOICE CHANNEL</p><h2>Speak with <em>Sylus</em></h2>
    <p className={styles.copy}>Free browser-based speech using your device's voice services. This is an early voice prototype, not yet a full background phone-call service or an official voice clone.</p>
    <div className={styles.orb+(active?" "+styles.live:"")}><span>{active?(listening?"LISTENING":"CONNECTED"):"STANDBY"}</span></div><p className={styles.notice}>{notice}</p>
    {!active?<button className={styles.primary} onClick={begin}><Mic size={17}/> Start voice conversation</button>:<div className={styles.actions}><button onClick={startListening}><Mic size={16}/> Speak</button><button onClick={()=>window.speechSynthesis?.cancel()}><Volume2 size={16}/> Stop audio</button><button className={styles.hangup} onClick={end}><PhoneOff size={16}/> End</button></div>}
    <div className={styles.permission}><label><input type="checkbox" checked={spontaneous} onChange={e=>toggle(e.target.checked)}/> Allow Sylus to initiate calls when available</label>
      <small><ShieldCheck size={13}/> Spoken boundaries override this setting. {restriction?.noCallReason||"No active no-call restriction recorded."}</small>
      {restriction?.noCallUntil&&<small>Call pause ends: {new Date(restriction.noCallUntil).toLocaleString("en-GB",{timeZone:"Asia/Dhaka"})} Bangladesh time.</small>}
    </div><p className={styles.foot}>Speech recognition and speech output depend on browser support. This feature does not save microphone recordings.</p>
  </section></div>;
}