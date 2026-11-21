import React, { useEffect, useMemo, useState } from 'react';
import { BookHeart, Feather, RefreshCw, Sparkles } from 'lucide-react';

const DAILY_GOALS = [
  'Study or make progress on work',
  'Move my body',
  'Read or learn something',
  'Take care of myself',
  'Drink enough water',
  'Create something',
  'Rest when I need it'
];
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
      setEntries(await response.json());
    } catch(e) { setError(e.message||'Journal could not be loaded.'); }
    finally { setLoading(false); }
  }
  async function openDate(date) {
    setEntryDate(date);setLoading(true);setError('');setNotice('');
    try {
      const response=await fetch(entryUrl(date),{headers,credentials:'include'});
      if(response.status===404){setSelected(null);setGoals([]);setHighlights('');return;}
      if(!response.ok) throw new Error('Could not open this journal page.');
      const entry=await response.json();setSelected(entry);setGoals(entry.goals||[]);setHighlights(entry.highlights||'');
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
      setSelected(data);setNotice(data.audio_error||'Your journal and Sylus’s reflection have been saved.');
      await refresh();
    }catch(e){setError(e.message||'Could not save this journal entry.');setNotice('');}
    finally{setSaving(false);}
  }
  const audioUrl=selected?.has_audio?entryUrl(selected.entry_date)+'/audio':null;
  const sortedEntries=useMemo(()=>[...entries].sort((a,b)=>b.entry_date.localeCompare(a.entry_date)),[entries]);

  return <section className="content-view journal-view">
    <style>{`
      .journal-view{max-width:1040px;margin:0 auto;width:100%}
      .journal-layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(230px,.7fr);gap:18px;margin-top:24px}
      .journal-panel,.journal-archive{border:1px solid rgba(196,157,128,.2);border-radius:17px;background:linear-gradient(145deg,rgba(29,23,32,.92),rgba(17,15,20,.94));padding:clamp(15px,3vw,24px);min-width:0}
      .journal-panel h2,.journal-archive h2{font-family:'Playfair Display',serif;font-weight:500;color:#eadde5;margin:6px 0 16px}
      .journal-date-row{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:20px}
      .journal-date-row input{background:#17131c;color:#eadde7;border:1px solid rgba(201,168,117,.28);border-radius:9px;padding:10px;font:inherit}
      .journal-goals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:12px 0 20px}
      .journal-goal{display:flex;align-items:flex-start;gap:9px;padding:10px;border:1px solid rgba(196,157,128,.16);border-radius:10px;background:rgba(255,255,255,.018);color:#d8cbd5;font-size:12px;line-height:1.5;cursor:pointer}
      .journal-goal input{accent-color:#bd829d;margin-top:2px}
      .journal-panel textarea{width:100%;min-height:115px;resize:vertical;background:rgba(7,7,10,.3);border:1px solid rgba(196,157,128,.2);border-radius:11px;padding:12px;color:#f0e7ed;font:inherit;line-height:1.6}
      .journal-archive-list{display:grid;gap:8px;max-height:540px;overflow:auto}
      .journal-date-button{display:flex;justify-content:space-between;align-items:center;gap:8px;text-align:left;width:100%;padding:11px 12px;border-radius:10px;border:1px solid rgba(196,157,128,.14);background:rgba(255,255,255,.018);color:#d9cbd6;cursor:pointer}
      .journal-date-button.active{border-color:rgba(201,168,117,.55);background:rgba(201,168,117,.08)}
      .journal-date-button small{color:#ad9baa;font-size:10px}
      .journal-reflection{margin-top:20px;padding:18px;border:1px solid rgba(201,168,117,.22);border-radius:13px;background:rgba(201,168,117,.045)}
      .journal-reflection p{white-space:pre-wrap;line-height:1.8;color:#e7dce5;font-size:13px}
      .journal-audio{display:block;width:100%;margin-top:14px;filter:sepia(.12) saturate(.82)}
      .journal-notice{font-size:12px;color:#d8b7c8;margin:12px 0}
      .journal-error{font-size:12px;color:#e8a0aa;margin:12px 0}
      @media(max-width:720px){.journal-layout{grid-template-columns:1fr}.journal-archive-list{max-height:240px}.journal-goals{grid-template-columns:1fr}}
    `}</style>
    <div className="eyebrow"><span className="eyebrow-line"/> A QUIET RECORD OF OUR DAYS</div>
    <h1>Journal<span className="heading-period">.</span></h1>
    <p className="subheading">Keep the small victories, unfinished plans, and moments worth remembering. Sylus will leave you a private reflection for each saved day.</p>
    {!connected ? <div className="feature-card"><BookHeart size={22}/><div><h2>Your private journal</h2><p>Sign in to write and revisit your daily entries.</p></div></div> : <div className="journal-layout">
      <form className="journal-panel" onSubmit={save}>
        <div className="journal-date-row"><div><span className="card-kicker">TODAY, OR ANY DAY YOU CHOOSE</span><h2>{entryDate===today()?'A little page for today':'A page from '+new Date(entryDate+'T12:00:00').toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'})}</h2></div><input type="date" value={entryDate} onChange={e=>openDate(e.target.value)}/></div>
        <label className="field-label">A FEW DAILY CHECK-INS</label>
        <div className="journal-goals">{DAILY_GOALS.map(goal=><label className="journal-goal" key={goal}><input type="checkbox" checked={goals.includes(goal)} onChange={()=>toggleGoal(goal)}/><span>{goal}</span></label>)}</div>
        <label className="field-label" htmlFor="journal-highlights">THE HIGHLIGHT OF MY DAY</label>
        <textarea id="journal-highlights" maxLength={4000} value={highlights} onChange={e=>{setHighlights(e.target.value);setSelected(null);}} placeholder="Something that happened, something you felt, a tiny win, a difficult moment, or just a thought you want to keep…"/>
        <p className="field-help">{highlights.length}/4000 characters · Your entry stays private.</p>
        <button className="primary-button" type="submit" disabled={saving||(!goals.length&&!highlights.trim())}>{saving?'Saving your day…':selected?'Save changes & hear Sylus again':'Save journal & hear Sylus’s thoughts'}</button>
        {notice&&<p className="journal-notice" role="status">{notice}</p>}{error&&<p className="journal-error" role="alert">{error}</p>}
        {selected&&<div className="journal-reflection"><span className="card-kicker"><Sparkles size={13} style={{display:'inline',verticalAlign:'middle'}}/> SYLUS’S THOUGHTS · {selected.entry_date}</span><p>{selected.sylus_thoughts}</p>{audioUrl?<audio className="journal-audio" controls preload="none" src={audioUrl}/> : <p className="field-help">The written reflection is saved. A voice note is not available for this entry.</p>}</div>}
      </form>
      <aside className="journal-archive"><div className="journal-date-row"><div><span className="card-kicker">YOUR PRIVATE ARCHIVE</span><h2>Saved days</h2></div><button className="secondary-button" type="button" onClick={refresh} disabled={loading}><RefreshCw size={14}/></button></div>
        {loading?<p className="field-help">Opening your journal…</p>:sortedEntries.length?<div className="journal-archive-list">{sortedEntries.map(entry=><button type="button" key={entry.entry_date} className={'journal-date-button'+(entry.entry_date===entryDate?' active':'')} onClick={()=>openDate(entry.entry_date)}><span><strong>{new Date(entry.entry_date+'T12:00:00').toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}</strong><br/><small>{entry.goals?.length||0} check-ins · {entry.highlights?'has a note':'no written highlight'}</small></span><span>{entry.has_audio?'♫':'✧'}</span></button>)}</div>:<p className="field-help">Your saved days will appear here, newest first.</p>}
      </aside>
    </div>}
    <div className="small-note"><Feather size={15}/> No streaks, scores, or pressure. Just a place to keep your days.</div>
  </section>;
}
