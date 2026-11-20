import React, { useEffect, useRef, useState } from 'react';

const DB_NAME = 'sylus-ringtone-library';
const STORE = 'ringtones';
const DB_VERSION = 1;

function openRingtoneDb() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) return reject(new Error('This browser does not support local audio storage.'));
    const request = window.indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Could not open ringtone storage.'));
  });
}

export async function getStoredRingtone(kind) {
  try {
    const db = await openRingtoneDb();
    return await new Promise((resolve, reject) => {
      const request = db.transaction(STORE, 'readonly').objectStore(STORE).get(kind);
      request.onsuccess = () => { resolve(request.result || null); db.close(); };
      request.onerror = () => { reject(request.error); db.close(); };
    });
  } catch { return null; }
}

async function saveStoredRingtone(kind, blob, name) {
  const db = await openRingtoneDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put({ blob, name, updatedAt: Date.now() }, kind);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error || new Error('Could not save ringtone.')); };
  });
}

async function deleteStoredRingtone(kind) {
  const db = await openRingtoneDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).delete(kind);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

function encodeWav(buffer) {
  const channels = Math.min(buffer.numberOfChannels, 2);
  const frames = buffer.length;
  const bytes = 2;
  const size = frames * channels * bytes;
  const output = new ArrayBuffer(44 + size);
  const view = new DataView(output);
  const write = (offset, value) => [...value].forEach((char, i) => view.setUint8(offset + i, char.charCodeAt(0)));
  write(0, 'RIFF'); view.setUint32(4, 36 + size, true); write(8, 'WAVE'); write(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, channels, true);
  view.setUint32(24, buffer.sampleRate, true); view.setUint32(28, buffer.sampleRate * channels * bytes, true);
  view.setUint16(32, channels * bytes, true); view.setUint16(34, 16, true); write(36, 'data'); view.setUint32(40, size, true);
  const data = Array.from({ length: channels }, (_, c) => buffer.getChannelData(c));
  let offset = 44;
  for (let i = 0; i < frames; i += 1) for (let c = 0; c < channels; c += 1) {
    const sample = Math.max(-1, Math.min(1, data[c][i]));
    view.setInt16(offset, sample < 0 ? sample * 32768 : sample * 32767, true);
    offset += 2;
  }
  return new Blob([output], { type: 'audio/wav' });
}

async function makePromptTone(description) {
  const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  if (!Offline) throw new Error('This browser cannot generate audio tones.');
  const words = description.toLowerCase();
  const dark = /dark|deep|ominous|danger|n109|mysterious|low|midnight/.test(words);
  const soft = /soft|gentle|tender|romantic|warm|heart|intimate|dream/.test(words);
  const metallic = /metal|steel|crystal|bell|chime|glass|spark/.test(words);
  const heartbeat = /heartbeat|pulse|throb/.test(words);
  const base = dark ? 146.83 : soft ? 392 : 293.66;
  const duration = 4.2;
  const ctx = new Offline(1, Math.ceil(44100 * duration), 44100);
  const master = ctx.createGain();
  master.gain.value = 0.72;
  const filter = ctx.createBiquadFilter();
  filter.type = metallic ? 'highpass' : 'lowpass';
  filter.frequency.value = metallic ? 520 : dark ? 1050 : 3600;
  master.connect(filter); filter.connect(ctx.destination);
  const notes = heartbeat
    ? [{f:base,t:.05,d:.18},{f:base*1.18,t:.28,d:.12},{f:base,t:1.15,d:.18},{f:base*1.18,t:1.38,d:.12},{f:base,t:2.5,d:.18},{f:base*1.18,t:2.73,d:.12}]
    : [{f:base,t:.08,d:.55},{f:base*1.25,t:.72,d:.5},{f:base*1.5,t:1.42,d:.72},{f:base*1.25,t:2.45,d:.48},{f:base*1.12,t:3.12,d:.75}];
  notes.forEach((note, index) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = metallic ? 'sine' : dark ? 'triangle' : 'sine';
    osc.frequency.setValueAtTime(note.f, note.t);
    if (metallic) {
      const overtone = ctx.createOscillator();
      const overtoneGain = ctx.createGain();
      overtone.type = 'sine'; overtone.frequency.value = note.f * 2.76;
      overtoneGain.gain.setValueAtTime(.12, note.t);
      overtoneGain.gain.exponentialRampToValueAtTime(.0001, note.t + note.d);
      overtone.connect(overtoneGain); overtoneGain.connect(master);
      overtone.start(note.t); overtone.stop(note.t + note.d + .02);
    }
    const peak = soft ? .24 : .34;
    gain.gain.setValueAtTime(.0001, note.t);
    gain.gain.exponentialRampToValueAtTime(peak, note.t + .035);
    gain.gain.exponentialRampToValueAtTime(.0001, note.t + note.d);
    osc.connect(gain); gain.connect(master);
    osc.start(note.t); osc.stop(note.t + note.d + .03);
  });
  const rendered = await ctx.startRendering();
  return encodeWav(rendered);
}

export default function RingtoneStudio({ onSaved }) {
  const [kind, setKind] = useState('message');
  const [description, setDescription] = useState('A dark, elegant N109 signal: low metallic resonance, a restrained heartbeat pulse, then a crystal chime.');
  const [fileName, setFileName] = useState('');
  const [decoded, setDecoded] = useState(null);
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [saved, setSaved] = useState({ message: null, call: null });
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const previewRef = useRef(null);
  const audioRef = useRef(null);
  const [previewUrl, setPreviewUrl] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([getStoredRingtone('message'), getStoredRingtone('call')]).then(([message, call]) => {
      if (active) setSaved({ message, call });
    });
    return () => { active = false; if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  function showPreview(blob) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const url = URL.createObjectURL(blob);
    setPreviewUrl(url);
    if (audioRef.current) {
      audioRef.current.src = url;
      audioRef.current.play().catch(() => setStatus('Tap Play preview to hear the audio.'));
    }
  }

  async function loadFile(file) {
    if (!file) return;
    if (file.size > 25 * 1024 * 1024) { setStatus('Please choose an audio file smaller than 25 MB.'); return; }
    setBusy(true); setStatus('Reading your audio…');
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      const buffer = await ctx.decodeAudioData(await file.arrayBuffer());
      await ctx.close();
      setDecoded(buffer); setStart(0); setEnd(Math.min(buffer.duration, 12)); setFileName(file.name);
      setStatus('Audio loaded. Choose a short section, then save it as a message or call ringtone.');
    } catch { setStatus('I could not read that audio format. Try MP3, WAV, M4A, AAC, OGG, or WebM.'); }
    finally { setBusy(false); }
  }

  async function saveTrimmed() {
    if (!decoded) return;
    const from = Math.max(0, Math.min(start, decoded.duration));
    const to = Math.max(from + .25, Math.min(end, decoded.duration, 20));
    const length = Math.max(1, Math.floor((to - from) * decoded.sampleRate));
    const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (!Offline) { setStatus('Audio trimming is not supported in this browser.'); return; }
    setBusy(true);
    try {
      const channels = Math.min(decoded.numberOfChannels, 2);
      const ctx = new Offline(channels, length, decoded.sampleRate);
      const source = ctx.createBufferSource();
      const cropped = ctx.createBuffer(channels, length, decoded.sampleRate);
      for (let c = 0; c < channels; c += 1) cropped.copyToChannel(decoded.getChannelData(c).slice(Math.floor(from * decoded.sampleRate), Math.floor(from * decoded.sampleRate) + length), c);
      source.buffer = cropped; source.connect(ctx.destination); source.start(0);
      const rendered = await ctx.startRendering();
      const blob = encodeWav(rendered);
      await saveStoredRingtone(kind, blob, fileName || 'Custom audio');
      setSaved(current => ({ ...current, [kind]: { blob, name: fileName || 'Custom audio' } }));
      showPreview(blob); onSaved?.(kind);
      setStatus(`Saved as your ${kind} ringtone.`);
    } catch (error) { setStatus(error.message || 'Could not save that ringtone.'); }
    finally { setBusy(false); }
  }

  async function generate() {
    if (!description.trim()) return;
    setBusy(true); setStatus('Composing an original sound from your description…');
    try {
      const blob = await makePromptTone(description);
      await saveStoredRingtone(kind, blob, 'Prompt composition');
      setSaved(current => ({ ...current, [kind]: { blob, name: 'Prompt composition' } }));
      showPreview(blob); onSaved?.(kind);
      setStatus(`Your original ${kind} sound is ready and saved on this device.`);
    } catch (error) { setStatus(error.message || 'Could not generate that sound.'); }
    finally { setBusy(false); }
  }

  function downloadSaved() {
    const item = saved[kind];
    if (!item?.blob) return;
    const url = URL.createObjectURL(item.blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sylus-${kind}-ringtone.wav`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function remove() {
    await deleteStoredRingtone(kind);
    setSaved(current => ({ ...current, [kind]: null }));
    onSaved?.(kind);
    setStatus(`Removed your custom ${kind} ringtone.`);
  }

  return <div className="ringtone-studio" style={{marginTop:18,padding:16,border:'1px solid rgba(196,157,128,.24)',borderRadius:14,background:'rgba(18,15,19,.34)'}}>
    <div className="card-kicker">PERSONAL SOUND DESIGN · N109</div>
    <h3 style={{margin:'6px 0 8px',fontFamily:'inherit'}}>Ringtone Atelier</h3>
    <p className="field-help">Make separate message and call sounds. Upload a clip and trim it, or describe an original sound for the built-in synthesizer to compose. Your audio stays in this browser on this device.</p>
    <label className="field-label" style={{marginTop:12}}>WHICH SOUND ARE YOU MAKING?</label>
    <div className="settings-actions">
      <button type="button" className={kind==='message'?'primary-button':'secondary-button'} onClick={()=>setKind('message')}>Message alert</button>
      <button type="button" className={kind==='call'?'primary-button':'secondary-button'} onClick={()=>setKind('call')}>Incoming call</button>
    </div>
    <div style={{marginTop:16}}>
      <label className="field-label">1 · UPLOAD YOUR AUDIO</label>
      <input ref={previewRef} type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.webm" className="settings-input" onChange={e=>loadFile(e.target.files?.[0])}/>
      {decoded && <div style={{marginTop:12}}>
        <p className="field-help">{fileName} · {decoded.duration.toFixed(1)} seconds</p>
        <label className="field-label">START · {start.toFixed(1)}s</label>
        <input type="range" min="0" max={Math.max(.1,Math.min(20,decoded.duration)-.25)} step=".1" value={Math.min(start,decoded.duration-.25)} onChange={e=>setStart(Number(e.target.value))} style={{width:'100%'}}/>
        <label className="field-label">END · {end.toFixed(1)}s (MAX 20 SECONDS)</label>
        <input type="range" min={Math.min(start+.25,decoded.duration)} max={Math.min(20,decoded.duration)} step=".1" value={Math.max(Math.min(end,20,decoded.duration),Math.min(start+.25,20,decoded.duration))} onChange={e=>setEnd(Number(e.target.value))} style={{width:'100%'}}/>
        <p className="field-help">Selected clip: {Math.max(0,end-start).toFixed(1)} seconds. Keep it short so the alert feels intentional.</p>
        <button type="button" className="secondary-button" onClick={()=>{const audio=new Audio();audio.src=URL.createObjectURL(encodeWav(decoded));audio.play().catch(()=>{});}}>Preview full upload</button>
        <button type="button" className="primary-button" style={{marginTop:8}} onClick={saveTrimmed} disabled={busy||end<=start}>Trim & save as {kind} ringtone</button>
      </div>}
    </div>
    <div className="settings-divider"/>
    <div>
      <label className="field-label">2 · DESCRIBE A SOUND</label>
      <textarea className="settings-input memory-textarea" rows={3} value={description} onChange={e=>setDescription(e.target.value)} placeholder="e.g. A low, elegant metallic pulse with a distant glass chime…"/>
      <p className="field-help">Try words like dark, metallic, crystal, heartbeat, soft, romantic, ominous, piano-like, or cinematic. This creates a synthesized ringtone locally; it is not full AI audio generation, an AI voice, or a copy of game music. You can download your saved sound as WAV for use in Android's ringtone settings.</p>
      <button type="button" className="primary-button" onClick={generate} disabled={busy||!description.trim()}>{busy?'Composing…':'Compose from description'}</button>
    </div>
    <div className="settings-divider"/>
    <div>
      <label className="field-label">3 · YOUR SAVED {kind.toUpperCase()} RINGTONE</label>
      <p className="field-help">{saved[kind] ? saved[kind].name || 'Custom sound saved' : 'No custom sound assigned yet. The original built-in tone will play until you save one.'}</p>
      <audio ref={audioRef} controls style={{width:'100%',margin:'8px 0'}}/>
      {saved[kind] && <div className="settings-actions"><button type="button" className="secondary-button" onClick={downloadSaved}>Download WAV</button><button type="button" className="secondary-button danger-action" onClick={remove}>Remove custom ringtone</button></div>}
    </div>
    {status && <p className="field-help" role="status" style={{marginTop:12}}>{status}</p>}
  </div>;
}
