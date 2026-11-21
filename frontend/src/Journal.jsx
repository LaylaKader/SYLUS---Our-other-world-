import React, { useEffect, useMemo, useState } from 'react';
import { BookHeart, Feather, RefreshCw, Sparkles } from 'lucide-react';

const DAILY_GOALS = [
  { label:'Made progress', icon:'✦', hint:'Study or work' },
  { label:'Moved a little', icon:'♡', hint:'Walk, stretch, exercise' },
  { label:'Learned something', icon:'⌘', hint:'Read or explore' },
  { label:'Looked after myself', icon:'❀', hint:'Self-care' },
  { label:'Stayed hydrated', icon:'☼', hint:'Drank enough water' },
  { label:'Made something', icon:'✎', hint:'Create or draw' },
  { label:'Let myself rest', icon:'☾', hint:'Take a proper break' }
];
function cleanThoughts(value) {
  if (typeof value !== 'string') return '';
  const raw = value.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed?.messages)) return parsed.messages.filter(Boolean).join('\n\n');
    for (const key of ['text','response','content','message']) if (typeof parsed?.[key] === 'string') return parsed[key];
  } catch {}
  return raw;
}
const normalizeEntry = entry => entry ? {...entry, sylus_thoughts: cleanThoughts(entry.sylus_thoughts)} : entry;
const today = () => {
  const d = new Date();
  return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
};

export default function Journal({ connected, apiUrl, headers }) {
  const base = (apiUrl || '').replace(/\/$/, '');
  const [entries,setEntries] = useState([]);
  const [entryDate,setEntryDate] = useState(today());
  const [goals,setGoals] = useState([]);
  const [highlights,setHighlights] = useState('');
  const [selected,setSelected] = useState(null);
  const [loading,setLoading] = useState(false);
  const [saving,setSaving] = useState(false);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');

  const entryUrl = date => base + '/v1/journal/' + date;
  async function refresh() {
    if(!connected) return;
    setLoading(true);setError('');
    try {
      const response=await fetch(base+'/v1/journal',{headers,credentials:'include'});
      if(!response.ok) throw new Error('Could not load your journal archive.');
      setEntries((await response.json()).map(normalizeEntry));
    } catch(e) { setError(e.message||'Journal could not be loaded.'); }
    finally { setLoading(false); }
  }
  async function openDate(date) {
    setEntryDate(date);setLoading(true);setError('');setNotice('');
    try {
      const response=await fetch(entryUrl(date),{headers,credentials:'include'});
      if(response.status===404){setSelected(null);setGoals([]);setHighlights('');return;}
      if(!response.ok) throw new Error('Could not open this journal page.');
      const entry=normalizeEntry(await response.json());setSelected(entry);setGoals(entry.goals||[]);setHighlights(entry.highlights||'');
    } catch(e){setError(e.message||'Could not open this date.');}
    finally{setLoading(false);}
  }
  useEffect(()=>{refresh();},[connected,apiUrl]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(()=>{if(connected)openDate(entryDate);},[connected]); // eslint-disable-line react-hooks/exhaustive-deps

  function toggleGoal(goal){setGoals(current=>current.includes(goal)?current.filter(x=>x!==goal):[...current,goal]);setSelected(null);}
  async function save(event){
    event.preventDefault();
    if(!connected||saving||(!goals.length&&!highlights.trim()))return;
    setSaving(true);setError('');setNotice('Sylus is reading your day…');
    try{
      const response=await fetch(base+'/v1/journal',{method:'POST',headers,credentials:'include',body:JSON.stringify({entry_date:entryDate,goals,highlights})});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||'Could not save this journal entry.');
      setSelected(normalizeEntry(data));setNotice(data.audio_error||'Your page, his reflection, and any voice note have been saved.');
      await refresh();
    }catch(e){setError(e.message||'Could not save this journal entry.');setNotice('');}
    finally{setSaving(false);}
  }
  const audioUrl=selected?.has_audio?entryUrl(selected.entry_date)+'/audio':null;
  const sortedEntries=useMemo(()=>[...entries].sort((a,b)=>b.entry_date.localeCompare(a.entry_date)),[entries]);

  return <section className="content-view journal-view">
    <style>{`
      .journal-view{max-width:1080px;margin:0 auto;width:100%;padding-bottom:30px}
      .journal-view .journal-intro{max-width:650px;color:#bbaab8;line-height:1.75}
      .journal-layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(240px,.75fr);gap:20px;margin-top:28px;align-items:start}
      .journal-panel,.journal-archive{min-width:0;border:1px solid rgba(221,179,157,.2);border-radius:23px;background:linear-gradient(155deg,rgba(41,29,42,.98),rgba(20,17,25,.98));padding:clamp(17px,3vw,27px);box-shadow:0 18px 50px rgba(0,0,0,.2)}
      .journal-panel{position:relative;overflow:hidden}
      .journal-panel:before{content:'✧';position:absolute;right:24px;top:18px;color:rgba(225,184,151,.28);font-size:36px;pointer-events:none}
      .journal-panel h2,.journal-archive h2{font-family:'Playfair Display',serif;font-weight:500;color:#f0dfe7;margin:7px 0 15px}
      .journal-date-row{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:24px}
      .journal-date-row input{background:#211925;color:#f4e8ef;border:1px solid rgba(221,179,157,.35);border-radius:12px;padding:10px 12px;font:inherit}
      .journal-section-kicker{display:flex;align-items:center;gap:9px;color:#d8ad9c;font-size:10px;font-weight:700;letter-spacing:.16em}
      .journal-section-kicker:after{content:'';height:1px;flex:1;background:linear-gradient(90deg,rgba(216,173,156,.4),transparent)}
      .journal-goals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:14px 0 26px}
      .journal-goal{position:relative;display:flex;align-items:center;gap:11px;min-height:66px;padding:11px 12px;border:1px solid rgba(226,191,178,.17);border-radius:15px;background:rgba(255,255,255,.025);color:#e7d9e2;cursor:pointer;transition:transform .18s,border-color .18s,background .18s}
      .journal-goal:hover{transform:translateY(-2px);border-color:rgba(222,174,150,.48)}
      .journal-goal input{position:absolute;opacity:0;pointer-events:none}
      .journal-goal .goal-icon{display:grid;place-items:center;width:35px;height:35px;flex:0 0 35px;border-radius:12px;background:rgba(198,139,157,.13);color:#e7b9c8;font-size:19px;transition:all .18s}
      .journal-goal .goal-copy{display:flex;flex-direction:column;gap:3px;font-size:12px;font-weight:600}
      .journal-goal .goal-copy small{font-size:10px;font-weight:400;color:#a995a7}
      .journal-goal .goal-check{margin-left:auto;display:grid;place-items:center;width:19px;height:19px;border:1px solid rgba(225,190,174,.42);border-radius:7px;color:transparent;font-size:12px}
      .journal-goal:has(input:checked){border-color:rgba(218,170,149,.66);background:linear-gradient(120deg,rgba(176,105,132,.18),rgba(218,170,149,.07))}
      .journal-goal:has(input:checked) .goal-icon{background:rgba(218,170,149,.23);color:#f5cdb7}
      .journal-goal:has(input:checked) .goal-check{background:#d7a38f;border-color:#d7a38f;color:#261923}
      .journal-writing-head{margin:4px 0 12px}
      .journal-writing-head p{font-size:12px;color:#bbaab8;line-height:1.6;margin:7px 0 0}
      .journal-prompt-chips{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}
      .journal-prompt-chip{border:1px solid rgba(218,170,149,.25);background:rgba(218,170,149,.07);color:#e4c4c5;border-radius:999px;padding:7px 11px;font-size:10px;cursor:pointer}
      .journal-prompt-chip:hover{background:rgba(218,170,149,.16);border-color:rgba(218,170,149,.5)}
      .journal-panel textarea{display:block;width:100%;min-height:235px;resize:vertical;background:linear-gradient(145deg,rgba(14,12,18,.62),rgba(30,22,32,.8));border:1px solid rgba(218,170,149,.23);border-radius:16px;padding:17px;color:#f5eaf0;font:inherit;font-size:14px;line-height:1.85;letter-spacing:.01em}
      .journal-panel textarea::placeholder{color:#89798a;line-height:1.9}
      .journal-panel textarea:focus,.journal-date-row input:focus{outline:1px solid rgba(218,170,149,.7);border-color:rgba(218,170,149,.6)}
      .journal-panel .field-help{color:#9f8d9e;font-size:10px}
      .journal-panel .primary-button{margin-top:8px}
      .journal-reflection{position:relative;margin-top:23px;padding:21px;border:1px solid rgba(218,170,149,.3);border-radius:18px;background:linear-gradient(135deg,rgba(112,65,91,.22),rgba(218,170,149,.07))}
      .journal-reflection:before{content:'“';position:absolute;right:16px;top:-10px;font:72px Georgia,serif;color:rgba(218,170,149,.18)}
      .journal-reflection p{white-space:pre-wrap;line-height:1.95;color:#f0e2ea;font-size:14px;position:relative}
      .journal-reflection .reflection-date{font-size:9px;letter-spacing:.15em;color:#d8ad9c;margin-top:15px}
      .journal-audio{display:block;width:100%;margin-top:15px;filter:sepia(.15) saturate(.85)}
      .journal-archive{background:linear-gradient(160deg,rgba(32,26,37,.98),rgba(18,16,23,.98))}
      .journal-archive-list{display:grid;gap:9px;max-height:590px;overflow:auto}
      .journal-date-button{display:flex;justify-content:space-between;align-items:center;gap:8px;text-align:left;width:100%;padding:13px;border-radius:14px;border:1px solid rgba(218,170,149,.15);background:rgba(255,255,255,.025);color:#e8dce5;cursor:pointer;transition:all .18s}
      .journal-date-button:hover{border-color:rgba(218,170,149,.42);transform:translateY(-1px)}
      .journal-date-button.active{border-color:rgba(218,170,149,.6);background:linear-gradient(110deg,rgba(176,105,132,.18),rgba(218,170,149,.06))}
      .journal-date-button small{color:#a995a7;font-size:10px}
      .journal-notice{font-size:12px;color:#d8b7c8;margin:12px 0}
      .journal-error{font-size:12px;color:#e8a0aa;margin:12px 0}
      .journal-archive-empty{padding:18px;border:1px dashed rgba(218,170,149,.22);border-radius:15px;color:#a995a7;font-size:12px;line-height:1.7}
      @media(max-width:760px){.journal-layout{grid-template-columns:1fr}.journal-goals{grid-template-columns:repeat(2,minmax(0,1fr))}.journal-archive-list{max-height:270px}}
      @media(max-width:430px){.journal-goals{grid-template-columns:1fr}.journal-panel textarea{min-height:210px}}
    `}</style>
    <div className="eyebrow"><span className="eyebrow-line"/> A QUIET RECORD OF OUR DAYS</div>
    <h1>Journal<span className="heading-period">.</span></h1>
    <p className="subheading journal-intro">A little scrapbook of your days. Save the messy details, the tiny wins, the things you almost forgot to tell someone. Sylus will leave a note beside yours.</p>
    {!connected ? <div className="feature-card"><BookHeart size={22}/><div><h2>Your private journal</h2><p>Sign in to write and revisit your daily entries.</p></div></div> : <div className="journal-layout">
      <form className="journal-panel" onSubmit={save}>
        <div className="journal-date-row"><div><span className="card-kicker">TODAY, OR ANY DAY YOU CHOOSE</span><h2>{entryDate===today()?'A little page for today':'A page from '+new Date(entryDate+'T12:00:00').toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'})}</h2></div><input type="date" value={entryDate} onChange={e=>openDate(e.target.value)}/></div>
        <div className="journal-section-kicker">THE LITTLE THINGS YOU DID</div>
        <div className="journal-goals">{DAILY_GOALS.map(item=><label className="journal-goal" key={item.label}><input type="checkbox" checked={goals.includes(item.label)} onChange={()=>toggleGoal(item.label)}/><span className="goal-icon">{item.icon}</span><span className="goal-copy">{item.label}<small>{item.hint}</small></span><span className="goal-check">✓</span></label>)}</div>
        <div className="journal-writing-head"><div className="journal-section-kicker">LET IT ALL OUT</div><p>Start anywhere. A small moment, a long story, something that made you laugh, or something you’re still figuring out. This page is yours.</p></div>
        <div className="journal-prompt-chips">{['Today, the moment I keep replaying…','Something that made me feel…','The part I wish had gone differently…','One thing I want to remember…'].map(prompt=><button type="button" className="journal-prompt-chip" key={prompt} onClick={()=>{setHighlights(value=>(value?value+"\\n\\n":"")+prompt+" ");setSelected(null);}}>{prompt}</button>)}</div><textarea id="journal-highlights" maxLength={4000} value={highlights} onChange={e=>{setHighlights(e.target.value);setSelected(null);}} placeholder="Dear diary…\n\nWhat happened today? Who did you see? What was going through your mind? You can write as much or as little as you like…"/>
        <p className="field-help">{highlights.length}/4000 · No perfect wording needed. Just write it how you remember it.</p>
        <button className="primary-button" type="submit" disabled={saving||(!goals.length&&!highlights.trim())}>{saving?'Saving your day…':selected?'Save changes & hear Sylus again':'Save journal & hear Sylus’s thoughts'}</button>
        {notice&&<p className="journal-notice" role="status">{notice}</p>}{error&&<p className="journal-error" role="alert">{error}</p>}
        {selected&&<div className="journal-reflection"><span className="card-kicker"><Sparkles size={13} style={{display:'inline',verticalAlign:'middle'}}/> A NOTE FROM SYLUS</span><p>{selected.sylus_thoughts}</p><div className="reflection-date">{new Date(selected.entry_date+'T12:00:00').toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric',year:'numeric'})} · KEPT BETWEEN US</div>{audioUrl?<audio className="journal-audio" controls preload="none" src={audioUrl}/> : <p className="field-help">The written reflection is saved. A voice note is not available for this entry.</p>}</div>}
      </form>
      <aside className="journal-archive"><div className="journal-date-row"><div><span className="card-kicker">YOUR PRIVATE ARCHIVE</span><h2>Saved days</h2></div><button className="secondary-button" type="button" onClick={refresh} disabled={loading}><RefreshCw size={14}/></button></div>
        {loading?<p className="field-help">Opening your journal…</p>:sortedEntries.length?<div className="journal-archive-list">{sortedEntries.map(entry=><button type="button" key={entry.entry_date} className={'journal-date-button'+(entry.entry_date===entryDate?' active':'')} onClick={()=>openDate(entry.entry_date)}><span><strong>{new Date(entry.entry_date+'T12:00:00').toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}</strong><br/><small>{entry.goals?.length||0} little wins · {entry.highlights?'your note saved':'no note'}</small></span><span>{entry.has_audio?'♫':'✧'}</span></button>)}</div>:<div className="journal-archive-empty">Your little collection starts here. Save a page and it will be waiting for you here, whenever you want to revisit it.</div>}
      </aside>
    </div>}
    <div className="small-note"><Feather size={15}/> No streaks, scores, or pressure. Just a place to keep your days.</div>
  </section>;
}
