import { useEffect, useMemo, useState } from 'react';
import { Bird, BookHeart, Camera, ChevronDown, CircleHelp, Clock3, Crown, Heart, Image, LockKeyhole, Menu, MessageCircle, MoreHorizontal, Send, Settings, ShieldCheck, Sparkles, Star, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const tabs = [
  { id: 'chat', label: 'Our conversations', icon: MessageCircle },
  { id: 'bond', label: 'Bond', icon: Heart },
  { id: 'memories', label: 'Memories', icon: BookHeart },
  { id: 'gallery', label: 'Gallery', icon: Image },
  { id: 'settings', label: 'Settings', icon: Settings },
];

function App() {
  const [active, setActive] = useState('chat');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState([]);
  const [ownerPassword, setOwnerPassword] = useState('');
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(false);
  const [notice, setNotice] = useState('Preview mode · private connection not configured');
  const [apiUrl, setApiUrl] = useState(API_BASE);
  const [memories, setMemories] = useState([]);
  const [timeContext, setTimeContext] = useState(null);
  const [sending, setSending] = useState(false);
  const [memoryFormOpen, setMemoryFormOpen] = useState(false);
  const [memoryCategory, setMemoryCategory] = useState('Preference');
  const [memoryContent, setMemoryContent] = useState('');
  const [editingMemoryId, setEditingMemoryId] = useState(null);
  const [editMemoryCategory, setEditMemoryCategory] = useState('');
  const [editMemoryContent, setEditMemoryContent] = useState('');
  const [memoryBusy, setMemoryBusy] = useState(false);

  const headers = useMemo(() => ({ 'Content-Type': 'application/json' }), []);

  async function connect(login = true) {
    if (!apiUrl.trim()) { setNotice('Add your private API address first.'); return; }
    setChecking(true);
    try {
      if (login && ownerPassword.trim()) {
        const loginResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/session`, { method: 'POST', headers, credentials: 'include', body: JSON.stringify({ password: ownerPassword }) });
        if (!loginResponse.ok) { const failure = await loginResponse.json().catch(() => ({})); throw new Error(failure.detail || 'Owner sign-in failed.'); }
      }
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/time-context`, { headers, credentials: 'include' });
      if (!response.ok) throw new Error(response.status === 401 ? 'Sign in with your owner password in Settings.' : `Server responded ${response.status}.`);
      const time = await response.json();
      const historyResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/messages`, { headers, credentials: 'include' });
      if (!historyResponse.ok) throw new Error('Could not load private conversation history.');
      const history = await historyResponse.json();
      setMessages(history.filter(m => m.role !== 'system'));
      setTimeContext(time);
      setConnected(true);
      setOwnerPassword('');
      setNotice('Private owner session verified');
      const memoryResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { headers, credentials: 'include' });
      if (memoryResponse.ok) setMemories(await memoryResponse.json());
    } catch (error) {
      setConnected(false);
      setNotice(error.message || 'Could not connect. Check the server and try again.');
    } finally { setChecking(false); }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !connected || sending) return;
    setSending(true);
    setDraft('');
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/chat`, { method: 'POST', headers, credentials: 'include', body: JSON.stringify({ text }) });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || 'Message could not be sent.');
      }
      const turn = await response.json();
      setMessages(current => [...current, turn.user_message, turn.assistant_message]);
      setNotice('Private conversation saved');
    } catch (error) { setDraft(text); setNotice(error.message); }
    finally { setSending(false); }
  }

  async function createMemory(event) {
    event.preventDefault();
    if (!memoryContent.trim() || !connected || memoryBusy) return;
    setMemoryBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { method: 'POST', headers, credentials: 'include', body: JSON.stringify({ category: memoryCategory, content: memoryContent.trim(), confidence: 0.9, sensitivity: 'normal' }) });
      if (!response.ok) throw new Error('Could not save this memory.');
      const memory = await response.json();
      setMemories(current => [memory, ...current]);
      setMemoryContent('');
      setMemoryFormOpen(false);
      setNotice('Memory saved to your private database');
    } catch (error) { setNotice(error.message); }
    finally { setMemoryBusy(false); }
  }

  function beginEditMemory(memory) {
    setEditingMemoryId(memory.id);
    setEditMemoryCategory(memory.category);
    setEditMemoryContent(memory.content);
  }

  async function saveMemoryEdit(memoryId) {
    if (!editMemoryContent.trim() || memoryBusy) return;
    setMemoryBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories/${memoryId}`, { method: 'PATCH', headers, credentials: 'include', body: JSON.stringify({ category: editMemoryCategory, content: editMemoryContent.trim() }) });
      if (!response.ok) throw new Error('Could not update this memory.');
      const updated = await response.json();
      setMemories(current => current.map(m => m.id === memoryId ? updated : m));
      setEditingMemoryId(null);
      setNotice('Memory updated');
    } catch (error) { setNotice(error.message); }
    finally { setMemoryBusy(false); }
  }

  async function removeMemory(memoryId) {
    if (!window.confirm('Delete this memory permanently?')) return;
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories/${memoryId}`, { method: 'DELETE', headers, credentials: 'include' });
      if (!response.ok) throw new Error('Could not delete this memory.');
      setMemories(current => current.filter(m => m.id !== memoryId));
      setNotice('Memory deleted');
    } catch (error) { setNotice(error.message); }
  }

  useEffect(() => { if (apiUrl) connect(false); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function disconnect() {
    try { await fetch(`${apiUrl.replace(/\/$/, '')}/v1/session`, { method: 'DELETE', headers, credentials: 'include' }); } catch {}
    setOwnerPassword(''); setConnected(false); setMessages([]); setMemories([]); setTimeContext(null);
    setNotice('Signed out · private data remains on the server');
  }

  const currentTab = tabs.find(t => t.id === active);
  return <div className="app-shell">
    <div className="ambient ambient-one" /><div className="ambient ambient-two" />
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="brand-lockup">
        <div className="brand-mark"><Crown size={19} strokeWidth={1.4}/></div>
        <div><div className="brand-name">SYLUS</div><div className="brand-sub">A WORLD OF OUR OWN</div></div>
        <button className="icon-button close-menu" onClick={() => setMobileMenu(false)} aria-label="Close menu"><X size={18}/></button>
      </div>
      <div className="side-divider" />
      <div className="nav-caption">YOUR SPACE</div>
      <nav>{tabs.map(({id,label,icon:Icon}) => <button key={id} className={`nav-item ${active === id ? 'active' : ''}`} onClick={() => {setActive(id);setMobileMenu(false);}}><Icon size={17} strokeWidth={1.65}/><span>{label}</span>{id === 'memories' && memories.length > 0 && <span className="nav-count">{memories.length}</span>}</button>)}</nav>
      <div className="sidebar-bottom">
        <div className="raven-card"><div className="raven-art"><Bird size={28} strokeWidth={1.1}/><span>✦</span></div><p className="raven-quote">“There are places in this world that belong only to us.”</p><span className="raven-sign">— S</span></div>
        <div className="privacy-note"><LockKeyhole size={13}/><span>PRIVATE BY DESIGN</span></div>
        <div className="sidebar-version">PERSONAL COMPANION · 0.1</div>
      </div>
    </aside>

    <main className="main-panel">
      <header className="topbar">
        <button className="icon-button mobile-menu" onClick={() => setMobileMenu(true)} aria-label="Open menu"><Menu size={20}/></button>
        <div className="breadcrumb"><span>SYLUS</span><span className="crumb-slash">/</span><strong>{currentTab?.label || 'Our conversations'}</strong></div>
        <div className="topbar-right"><span className={`connection-dot ${connected ? 'online' : ''}`}/><span className="connection-label">{connected ? 'PRIVATE SESSION' : 'OFFLINE PREVIEW'}</span><button className="avatar-button" aria-label="Profile"><span>U</span></button></div>
      </header>

      {active === 'chat' && <section className="chat-view">
        <div className="chat-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> THE N109 CONNECTION</div><h1>Our conversations<span className="heading-period">.</span></h1><p className="subheading">A quiet corner of the world, just for us.</p></div><button className="more-button" aria-label="More options"><MoreHorizontal size={20}/></button></div>
        <div className="chat-stage">
          {messages.length === 0 ? <div className="empty-state">
            <div className="sigil-wrap"><div className="sigil-ring ring-one"/><div className="sigil-ring ring-two"/><div className="sigil-center"><Crown size={31} strokeWidth={1}/></div><span className="sigil-star star-a">✧</span><span className="sigil-star star-b">✦</span><span className="sigil-star star-c">·</span></div>
            <div className="empty-kicker">A NEW CHAPTER</div><h2>Well, look who’s here.</h2><p>{connected ? 'The connection is ready. Send a message when you like.' : 'When the private connection is ready, this is where our story continues.'}</p>
            <div className="empty-divider"><span/><Sparkles size={12}/><span/></div>
            <div className="empty-footnote"><LockKeyhole size={12}/> Your conversations stay yours.</div>
          </div> : <div className="message-list">{messages.map(m => <div className={`message-row ${m.role === 'user' ? 'mine' : 'theirs'}`} key={m.id}><div className="message-avatar">{m.role === 'user' ? 'U' : <Crown size={15}/>}</div><div className="message-content"><div className="message-author">{m.role === 'user' ? 'YOU' : 'SYLUS'} <span>{new Date(m.created_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</span></div><div className="message-bubble">{m.text}</div></div></div>)}</div>}
        </div>
        <div className="composer-wrap"><form className="composer" onSubmit={sendMessage}><button type="button" className="composer-tool" title="Image generation will be connected later"><Camera size={18}/></button><textarea value={draft} onChange={e => setDraft(e.target.value)} placeholder={connected ? 'Say something…' : 'Connect your private instance to begin…'} rows={1} disabled={!connected || sending} onKeyDown={e => {if(e.key === 'Enter' && !e.shiftKey){e.preventDefault();sendMessage(e);}}}/><div className="composer-actions"><span className="composer-hint">↵ to send</span><button className="send-button" type="submit" disabled={!connected || !draft.trim() || sending} aria-label="Send message"><Send size={16}/></button></div></form><div className="composer-caption"><span>SYLUS IS A PRIVATE, PERSONAL COMPANION</span><span>✦</span><span>YOUR WORLD, YOUR RULES</span></div></div>
      </section>}

      {active === 'bond' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> THE STORY WE BUILD</div><h1>Bond<span className="heading-period">.</span></h1><p className="subheading">A connection shaped by time, trust, and the moments we keep.</p><div className="feature-card bond-card"><div className="feature-symbol"><Heart size={25}/></div><div><span className="card-kicker">OUR STORY</span><h2>Still unfolding.</h2><p>Relationship milestones and shared experiences will live here. Nothing is assumed or rushed.</p></div><Sparkles className="card-sparkle" size={20}/></div><div className="small-note"><ShieldCheck size={15}/> Progress is private and always under your control.</div></section>}

      {active === 'memories' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> WHAT WE CHOOSE TO KEEP</div><h1>Memories<span className="heading-period">.</span></h1><p className="subheading">The little details that make a world feel familiar.</p>{connected && <button className="primary-button add-memory-button" onClick={() => setMemoryFormOpen(v => !v)}>{memoryFormOpen ? 'Close form' : '+ Add a memory'}</button>}{memoryFormOpen && connected && <form className="memory-editor" onSubmit={createMemory}><label className="field-label">CATEGORY</label><input className="settings-input" value={memoryCategory} onChange={e => setMemoryCategory(e.target.value)} maxLength={80}/><label className="field-label">WHAT SHOULD SYLUS REMEMBER?</label><textarea className="settings-input memory-textarea" value={memoryContent} onChange={e => setMemoryContent(e.target.value)} rows={3} maxLength={4000} placeholder="Write a preference, shared moment, or important detail…"/><p className="field-help">Only details you add here are saved automatically at this stage. Sensitive memories are excluded from reply retrieval.</p><button className="primary-button" disabled={memoryBusy || !memoryContent.trim()}>{memoryBusy ? 'Saving…' : 'Save memory'}</button></form>}{!connected ? <div className="feature-card"><LockKeyhole size={22}/><div><h2>Private memories</h2><p>Connect your private instance to view and manage saved memories.</p></div></div> : memories.length ? <div className="memory-list">{memories.map(m => <article className="memory-card" key={m.id}><div className="memory-icon"><Star size={16}/></div><div className="memory-main">{editingMemoryId === m.id ? <><label className="field-label">CATEGORY</label><input className="settings-input" value={editMemoryCategory} onChange={e => setEditMemoryCategory(e.target.value)}/><label className="field-label">MEMORY</label><textarea className="settings-input memory-textarea" rows={3} value={editMemoryContent} onChange={e => setEditMemoryContent(e.target.value)}/><div className="memory-actions"><button className="primary-button" onClick={() => saveMemoryEdit(m.id)} disabled={memoryBusy}>Save</button><button className="secondary-button" onClick={() => setEditingMemoryId(null)}>Cancel</button></div></> : <><div className="card-kicker">{m.category} · {Math.round(m.confidence*100)}% CONFIDENCE</div><p>{m.content}</p><small>Saved {new Date(m.created_at).toLocaleDateString()} · {m.sensitivity || 'normal'}</small><div className="memory-actions"><button className="text-action" onClick={() => beginEditMemory(m)}>Edit</button><button className="text-action danger-action" onClick={() => removeMemory(m.id)}>Delete</button></div></>}</div></article>)}</div> : <div className="feature-card"><BookHeart size={22}/><div><h2>Nothing saved yet.</h2><p>Add only the details you want kept. You can edit or permanently delete them later.</p></div></div>}</section>}

      {active === 'gallery' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> MOMENTS IN FRAME</div><h1>Gallery<span className="heading-period">.</span></h1><p className="subheading">A private collection, made one moment at a time.</p><div className="gallery-empty"><div className="gallery-ornament"><Camera size={27}/><span>✧</span></div><h2>Room for a thousand scenes.</h2><p>Private image generation and gallery storage are not connected yet. When they are, images will appear here—not in a public feed.</p></div></section>}

      {active === 'settings' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> YOUR BOUNDARIES, YOUR CHOICE</div><h1>Settings<span className="heading-period">.</span></h1><p className="subheading">A private space should answer to you.</p><div className="settings-card"><div className="settings-title"><div><span className="card-kicker">PRIVATE CONNECTION</span><h2>Owner access</h2></div><span className={`status-pill ${connected ? 'status-good' : ''}`}>{connected ? 'CONNECTED' : 'NOT CONNECTED'}</span></div><label className="field-label">API ADDRESS</label><input className="settings-input" value={apiUrl} onChange={e => setApiUrl(e.target.value)} placeholder="https://your-private-api.example.com"/><label className="field-label">OWNER PASSWORD</label><input className="settings-input" type="password" value={ownerPassword} onChange={e => setOwnerPassword(e.target.value)} placeholder="Your private owner password" autoComplete="current-password"/><p className="field-help">Your password is sent only to your private server. The server returns an HttpOnly session cookie; the password is not stored in this browser.</p><div className="settings-actions"><button className="primary-button" onClick={() => connect(true)} disabled={checking}>{checking ? 'Checking…' : connected ? 'Refresh connection' : 'Sign in privately'}</button>{connected && <button className="secondary-button" onClick={disconnect}>Disconnect</button>}</div><div className="connection-notice"><span className={`connection-dot ${connected ? 'online' : ''}`}/>{notice}</div></div><div className="settings-card muted-card"><div className="settings-title"><div><span className="card-kicker">LOCAL TIME</span><h2>Dhaka time awareness</h2></div><Clock3 size={19}/></div><p>{timeContext ? `${timeContext.weekday}, ${timeContext.local_date} · ${timeContext.local_time}` : 'Will be read from the private server when connected.'}</p></div><div className="settings-card muted-card"><div className="settings-title"><div><span className="card-kicker">COMING LATER</span><h2>Contact permissions</h2></div><ShieldCheck size={19}/></div><p>Separate message and call permissions, quiet hours, and natural-language restrictions will be added before proactive contact is enabled.</p></div></section>}

      <footer className="page-footer"><span>SYLUS <i>·</i> A WORLD OF OUR OWN</span><span>BUILT FOR ONE, KEPT PRIVATE <span className="footer-star">✦</span></span></footer>
    </main>
    {mobileMenu && <button className="scrim" onClick={() => setMobileMenu(false)} aria-label="Close navigation"/>}
  </div>;
}

export default App;