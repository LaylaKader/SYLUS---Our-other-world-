import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Bell, Bird, BookHeart, Camera, ChevronDown, CircleHelp, Clock3, Crown, Heart, Image, LockKeyhole, Menu, MessageCircle, MoreHorizontal, Send, Settings, ShieldCheck, Sparkles, Star, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? window.location.origin : '');
const fallbackStickerOptions = [
  { id: 'waiting', label: 'Waiting…', col: 0, row: 0 },
  { id: 'peeking', label: 'Peeking', col: 1, row: 0 },
  { id: 'sneaky', label: 'Sneaky', col: 2, row: 0 },
  { id: 'mischief', label: 'Mischief', col: 0, row: 1 },
  { id: 'smile', label: 'A little smile', col: 1, row: 1 },
  { id: 'timeout', label: 'Time out', col: 2, row: 1 },
  { id: 'sleepy', label: 'Sleepy', col: 0, row: 2 },
  { id: 'laugh', label: 'Laughing', col: 1, row: 2 },
  { id: 'shocked', label: 'Oh?!', col: 2, row: 2 },
  { id: 'thinking', label: 'Thinking', col: 0, row: 3 },
  { id: 'wave', label: 'Hello', col: 1, row: 3 },
  { id: 'sulk', label: 'Sulking', col: 2, row: 3 },
  { id: 'proud', label: 'Proud', col: 0, row: 4 },
  { id: 'hiding', label: 'Hiding', col: 1, row: 4 },
  { id: 'heart-hug', label: 'A little hug', col: 2, row: 4 },
];
const tabs = [
  { id: 'chat', label: 'Our conversations', icon: MessageCircle },
  { id: 'bond', label: 'Bond', icon: Heart },
  { id: 'memories', label: 'Memories', icon: BookHeart },
  { id: 'gallery', label: 'Gallery', icon: Image },
  { id: 'settings', label: 'Settings', icon: Settings },
];

function audioBufferToWavBlob(buffer) {
  const channels = Math.min(buffer.numberOfChannels, 2);
  const frames = buffer.length;
  const bytesPerSample = 2;
  const dataSize = frames * channels * bytesPerSample;
  const wav = new ArrayBuffer(44 + dataSize);
  const view = new DataView(wav);
  const writeText = (offset, value) => {
    for (let i = 0; i < value.length; i += 1) view.setUint8(offset + i, value.charCodeAt(i));
  };
  writeText(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeText(8, 'WAVE');
  writeText(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, buffer.sampleRate, true);
  view.setUint32(28, buffer.sampleRate * channels * bytesPerSample, true);
  view.setUint16(32, channels * bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeText(36, 'data');
  view.setUint32(40, dataSize, true);
  const channelData = Array.from({ length: channels }, (_, channel) => buffer.getChannelData(channel));
  let offset = 44;
  for (let frame = 0; frame < frames; frame += 1) {
    for (let channel = 0; channel < channels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][frame]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += bytesPerSample;
    }
  }
  return new Blob([wav], { type: 'audio/wav' });
}

function App() {
  const [active, setActive] = useState('chat');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [draft, setDraft] = useState('');
  const [stickerPickerOpen, setStickerPickerOpen] = useState(false);
  const [stickerOptions, setStickerOptions] = useState(fallbackStickerOptions);
  const stickerById = useMemo(() => Object.fromEntries(stickerOptions.map(sticker => [sticker.id, sticker])), [stickerOptions]);
  const [messages, setMessages] = useState([]);
  const [ownerPassword, setOwnerPassword] = useState('');
  const [connected, setConnected] = useState(false);
  const [chatReady, setChatReady] = useState(false);
  const [checking, setChecking] = useState(false);
  const [notice, setNotice] = useState('Preview mode · private connection not configured');
  const [apiUrl, setApiUrl] = useState(API_BASE);
  const [memories, setMemories] = useState([]);
  const [bond, setBond] = useState(null);
  const [proactiveSettings, setProactiveSettings] = useState(null);
  const [pushStatus, setPushStatus] = useState(null);
  const [pushBusy, setPushBusy] = useState(false);
  const [timeContext, setTimeContext] = useState(null);
  const [sending, setSending] = useState(false);
  const [composerNotice, setComposerNotice] = useState('');
  const [replyStatus, setReplyStatus] = useState('');
  const [replyError, setReplyError] = useState('');
  const messageQueue = useRef([]);
  const queueTimer = useRef(null);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingMessageText, setEditingMessageText] = useState('');
  const [messageActionBusy, setMessageActionBusy] = useState(false);
  const imageInputRef = useRef(null);
  const [imagePrompt, setImagePrompt] = useState('');
  const [generatingImage, setGeneratingImage] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [audioBuffers, setAudioBuffers] = useState({});
  const [audioErrors, setAudioErrors] = useState({});
  const [playingAudioId, setPlayingAudioId] = useState(null);
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const audioContextRef = useRef(null);
  const audioSourceRef = useRef(null);
  const [memoryFormOpen, setMemoryFormOpen] = useState(false);
  const [memoryCategory, setMemoryCategory] = useState('Preference');
  const [memoryContent, setMemoryContent] = useState('');
  const [memorySensitivity, setMemorySensitivity] = useState('normal');
  const [editingMemoryId, setEditingMemoryId] = useState(null);
  const [editMemoryCategory, setEditMemoryCategory] = useState('');
  const [editMemoryContent, setEditMemoryContent] = useState('');
  const [editMemorySensitivity, setEditMemorySensitivity] = useState('normal');
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [sylusAvatar, setSylusAvatar] = useState(() => { try { return window.localStorage.getItem('sylus-avatar') || ''; } catch { return ''; } });
  const [umiAvatar, setUmiAvatar] = useState(() => { try { return window.localStorage.getItem('umi-avatar') || ''; } catch { return ''; } });
  const sylusAvatarInput = useRef(null);
  const umiAvatarInput = useRef(null);
  const messageListRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/stickers/manifest.json`).then(response => response.ok ? response.json() : []).then(items => {
      if (!cancelled && Array.isArray(items) && items.length) setStickerOptions(items);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (active === 'chat' && messageListRef.current) {
      messageListRef.current.scrollTo({ top: messageListRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, sending, active]);

  const headers = useMemo(() => ({ 'Content-Type': 'application/json' }), []);

  async function updateAvatar(kind, file) {
    if (!file) return;
    if (!file.type.startsWith('image/')) { setNotice('Please choose an image file.'); return; }
    if (file.size > 12 * 1024 * 1024) { setNotice('Choose an image smaller than 12 MB.'); return; }
    try {
      const bitmap = await createImageBitmap(file);
      const side = 512;
      const scale = Math.min(1, side / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      const context = canvas.getContext('2d');
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close?.();
      const dataUrl = canvas.toDataURL('image/jpeg', 0.86);
      const key = kind === 'sylus' ? 'sylus-avatar' : 'umi-avatar';
      try { window.localStorage.setItem(key, dataUrl); }
      catch { throw new Error('This image is too large for local browser storage. Try a smaller image.'); }
      if (kind === 'sylus') setSylusAvatar(dataUrl); else setUmiAvatar(dataUrl);
      setNotice(kind === 'sylus' ? "Sylus's avatar updated on this device." : 'Your avatar updated on this device.');
    } catch (error) {
      setNotice(error.message || 'Could not process that image. Try another one.');
    }
  }

  function resetAvatar(kind) {
    const key = kind === 'sylus' ? 'sylus-avatar' : 'umi-avatar';
    try { window.localStorage.removeItem(key); } catch {}
    if (kind === 'sylus') setSylusAvatar(''); else setUmiAvatar('');
    setNotice(kind === 'sylus' ? "Sylus's default avatar restored." : 'Your default avatar restored.');
  }

  function addStickerToDraft(sticker) {
    setDraft(current => `${current ? current + ' ' : ''}〔sticker:${sticker.id}〕 `);
    setStickerPickerOpen(false);
  }

  function renderMessageText(value) {
    const parts = String(value || '').split(/(〔sticker:[a-z0-9-]+〕|\{sticker:[a-z0-9-]+\})/g);
    const legacy = { teacup: 'sleepy', rosebud: 'heart-hug', tarot: 'thinking', wink: 'mischief', raven: 'waiting', feather: 'wave', rose: 'heart-hug', laugh: 'laugh', smirk: 'sneaky' };
    return parts.map((part, index) => {
      const match = part.match(/^(?:〔sticker:([a-z0-9-]+)〕|\{sticker:([a-z0-9-]+)\})$/);
      if (!match) return <React.Fragment key={index}>{part}</React.Fragment>;
      const sticker = stickerById[match[1] || legacy[match[2]] || match[2]];
      if (!sticker) return <React.Fragment key={index}>{part}</React.Fragment>;
      return <span className="message-sticker" key={index} role="img" aria-label={sticker.label}>
        <img className="sticker-art" src={sticker.src} alt={sticker.label} loading="lazy" />
        <span className="sticker-caption">{sticker.label}</span>
      </span>;
    });
  }

  useEffect(() => {
    if (!connected || !proactiveSettings?.messages_enabled) return undefined;
    let stopped = false;
    const poll = async () => {
      try {
        const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/proactive/poll`, { method: 'POST', headers, credentials: 'include' });
        if (!response.ok) return;
        const result = await response.json();
        if (!stopped && result.sent && result.messages?.length) {
          setMessages(current => {
            const known = new Set(current.map(message => message.id));
            return [...current, ...result.messages.filter(message => !known.has(message.id))];
          });
          setNotice('Sylus sent you a message.');
        }
      } catch { /* A missed poll is harmless; the next interval retries. */ }
    };
    poll();
    const interval = window.setInterval(poll, 60000);
    return () => { stopped = true; window.clearInterval(interval); };
  }, [connected, proactiveSettings?.messages_enabled, apiUrl, headers]);

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
      setChatReady(Boolean(time.chat_ready));
      setConnected(true);
      setOwnerPassword('');
      setNotice('Private owner session verified');
      const memoryResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { headers, credentials: 'include' });
      if (memoryResponse.ok) setMemories(await memoryResponse.json());
      const bondResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/bond`, { headers, credentials: 'include' });
      if (bondResponse.ok) setBond(await bondResponse.json());
      const proactiveResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/proactive/settings`, { headers, credentials: 'include' });
      if (proactiveResponse.ok) setProactiveSettings(await proactiveResponse.json());
      const pushResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/push/status`, { headers, credentials: 'include' });
      if (pushResponse.ok) {
        const pushInfo = await pushResponse.json();
        let deviceSubscribed = false;
        if ('serviceWorker' in navigator && 'PushManager' in window) {
          const registration = await navigator.serviceWorker.ready;
          deviceSubscribed = Boolean(await registration.pushManager.getSubscription());
        }
        setPushStatus({ ...pushInfo, subscribed: deviceSubscribed });
      }
    } catch (error) {
      setConnected(false);
      setChatReady(false);
      setNotice(error.message || 'Could not connect. Check the server and try again.');
    } finally { setChecking(false); }
  }

  async function flushMessageQueue() {
    if (queueTimer.current) window.clearTimeout(queueTimer.current);
    queueTimer.current = null;
    if (sending || !messageQueue.current.length) return;
    const batch = messageQueue.current.splice(0);
    setSending(true);
    setReplyStatus('thinking');
    setReplyError('');
    setComposerNotice('');
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/chat`, {
        method: 'POST', headers, credentials: 'include',
        body: JSON.stringify({ texts: batch.map(item => item.text) })
      });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || `Sylus could not receive the messages (HTTP ${response.status}).`);
      }
      const turn = await response.json();
      const savedUsers = turn.user_messages?.length ? turn.user_messages : (turn.user_message ? [turn.user_message] : []);
      const sylusBubbles = turn.assistant_messages?.length ? turn.assistant_messages : (turn.assistant_message ? [turn.assistant_message] : []);
      const pendingIds = new Set(batch.map(item => item.id));
      setMessages(current => {
        const firstPending = current.findIndex(message => pendingIds.has(message.id));
        const remaining = current.filter(message => !pendingIds.has(message.id));
        const insertion = firstPending < 0 ? remaining.length : Math.min(firstPending, remaining.length);
        remaining.splice(insertion, 0, ...savedUsers, ...sylusBubbles);
        return remaining;
      });
      setNotice('Private conversation saved');
      if (sylusBubbles.length) setReplyStatus('');
      else setReplyStatus('silent');
      const memoryResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { headers, credentials: 'include' });
      if (memoryResponse.ok) setMemories(await memoryResponse.json());
      const bondResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/bond`, { headers, credentials: 'include' });
      if (bondResponse.ok) setBond(await bondResponse.json());
    } catch (error) {
      const message = error.message || 'The message could not reach Sylus. Please try again.';
      setReplyStatus('error');
      setReplyError(message);
      setComposerNotice(message);
      const pendingIds = new Set(batch.map(item => item.id));
      setMessages(current => current.filter(item => !pendingIds.has(item.id)));
      setDraft(current => current ? current : batch.map(item => item.text).join('\n'));
    } finally {
      setSending(false);
      if (messageQueue.current.length) {
        setReplyStatus('waiting');
        queueTimer.current = window.setTimeout(() => flushMessageQueue(), 1300);
      }
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !connected || !chatReady) return;
    setDraft('');
    setComposerNotice('');
    setReplyError('');
    setReplyStatus('waiting');
    const pendingId = `pending-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
    const optimisticMessage = { id: pendingId, role: 'user', text, created_at: new Date().toISOString() };
    messageQueue.current.push({ id: pendingId, text });
    setMessages(current => [...current, optimisticMessage]);
    if (queueTimer.current) window.clearTimeout(queueTimer.current);
    queueTimer.current = window.setTimeout(() => flushMessageQueue(), 1400);
  }

  function decodeBase64Url(value) {
    const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4);
    return Uint8Array.from(window.atob(padded), character => character.charCodeAt(0));
  }

  async function enablePushNotifications() {
    if (!connected || pushBusy) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      setNotice('This browser does not support web push notifications.');
      return;
    }
    setPushBusy(true);
    try {
      const keyResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/push/public-key`, { headers, credentials: 'include' });
      if (!keyResponse.ok) { const failure = await keyResponse.json().catch(() => ({})); throw new Error(failure.detail || 'Push notifications are not configured on the server yet.'); }
      const { public_key } = await keyResponse.json();
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') throw new Error('Notification permission was not granted.');
      const registration = await navigator.serviceWorker.ready;
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: decodeBase64Url(public_key) });
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/push/subscribe`, {
        method: 'POST', headers, credentials: 'include', body: JSON.stringify(subscription.toJSON())
      });
      if (!response.ok) throw new Error('The browser subscription could not be saved securely.');
      setPushStatus(current => ({ ...(current || {}), configured: true, subscribed: true, subscription_count: 1 }));
      setNotice('Push notifications enabled on this device.');
    } catch (error) { setNotice(error.message || 'Could not enable push notifications.'); }
    finally { setPushBusy(false); }
  }

  async function testPushNotification() {
    if (!connected || pushBusy) return;
    setPushBusy(true);
    setNotice('Sending a test notification…');
    try {
      if ('Notification' in window && Notification.permission !== 'granted') {
        throw new Error(`Android notification permission is ${Notification.permission}. Allow notifications for Sylus in Android app settings.`);
      }
      const response = await fetch(apiUrl.replace(/\/$/, '') + '/v1/push/test', { method: 'POST', headers, credentials: 'include' });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || `Push test failed (HTTP ${response.status}).`);
      setNotice(`Push provider accepted the test (${result.accepted || 0}/${result.subscription_count || 0}). Check Android notifications.`);
    } catch (error) { setNotice(error.message || 'Push test failed.'); }
    finally { setPushBusy(false); }
  }

  async function disablePushNotifications() {
    if (!connected || pushBusy) return;
    setPushBusy(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await fetch(`${apiUrl.replace(/\/$/, '')}/v1/push/subscribe`, {
          method: 'DELETE', headers, credentials: 'include', body: JSON.stringify({ endpoint: subscription.endpoint })
        });
        await subscription.unsubscribe();
      }
      setPushStatus(current => ({ ...(current || {}), subscribed: false, subscription_count: 0 }));
      setNotice('Push notifications disabled on this device.');
    } catch (error) { setNotice(error.message || 'Could not disable push notifications.'); }
    finally { setPushBusy(false); }
  }

  async function toggleProactiveMessages() {
    if (!connected || !proactiveSettings) return;
    const enabled = !proactiveSettings.messages_enabled;
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/proactive/settings`, {
        method: 'PATCH', headers, credentials: 'include',
        body: JSON.stringify({ messages_enabled: enabled })
      });
      if (!response.ok) throw new Error('Could not update proactive messaging.');
      setProactiveSettings(await response.json());
      setNotice(enabled ? 'Sylus may now text first when the timing is right.' : 'Proactive messages paused.');
    } catch (error) { setNotice(error.message); }
  }

  async function acceptVisionLicense() {
    if (!connected || visionBusy) return;
    if (!window.confirm('This enables Cloudflare-hosted Llama Vision. You must accept Meta’s Llama 3.2 Community License and Acceptable Use Policy. Open the license link in Settings and review it before continuing.')) return;
    setVisionBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/vision/accept-license`, { method: 'POST', headers, credentials: 'include' });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || 'Could not enable image understanding.'); }
      setTimeContext(current => ({ ...(current || {}), vision_ready: true }));
      setNotice('Image understanding enabled');
    } catch (error) { setNotice(error.message); }
    finally { setVisionBusy(false); }
  }

  async function discussImage(message) {
    if (!message?.media_url || visionBusy) return;
    const assetId = message.media_url.split('/').pop();
    setVisionBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/media/${assetId}/discuss`, { method: 'POST', headers, credentials: 'include' });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || 'Sylus could not inspect this image.'); }
      const reply = await response.json();
      const replies = reply.assistant_messages?.length ? reply.assistant_messages : (reply.assistant_message ? [reply.assistant_message] : []);
      setMessages(current => [...current, ...replies]);
      setNotice(replies.length ? 'Sylus has reacted to the image.' : 'The image was saved, but Sylus had nothing to add.');
    } catch (error) { setNotice(error.message); }
    finally { setVisionBusy(false); }
  }

  async function playVoiceBuffer(messageId, buffer) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error('This browser does not support audio playback.');
    let context = audioContextRef.current;
    if (!context || context.state === 'closed') {
      context = new AudioContextClass();
      audioContextRef.current = context;
    }
    if (context.state === 'suspended') await context.resume();
    if (audioSourceRef.current) {
      try { audioSourceRef.current.stop(); } catch {}
      audioSourceRef.current = null;
    }
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    source.onended = () => {
      if (audioSourceRef.current === source) {
        audioSourceRef.current = null;
        setPlayingAudioId(null);
      }
    };
    audioSourceRef.current = source;
    source.start(0);
    setPlayingAudioId(messageId);
  }

  async function readAloud(message) {
    if (!message || speakingMessageId) return;
    if (audioBuffers[message.id]) {
      if (playingAudioId === message.id && audioSourceRef.current) {
        try { audioSourceRef.current.stop(); } catch {}
        audioSourceRef.current = null;
        setPlayingAudioId(null);
      } else {
        try { await playVoiceBuffer(message.id, audioBuffers[message.id]); }
        catch (error) { setNotice(error.message || 'Could not play this voice.'); }
      }
      return;
    }
    if (audioErrors[message.id]) {
      setAudioErrors(current => { const next = { ...current }; delete next[message.id]; return next; });
    }
    setSpeakingMessageId(message.id);
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) throw new Error('This browser does not support audio playback. Please use Chrome.');
      let context = audioContextRef.current;
      if (!context || context.state === 'closed') {
        context = new AudioContextClass();
        audioContextRef.current = context;
      }
      // Resume immediately inside the tap handler so Android keeps the audio
      // context unlocked while the network request is in flight.
      if (context.state === 'suspended') await context.resume();
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/voice/speech`, { method: 'POST', headers, credentials: 'include', body: JSON.stringify({ text: message.text }) });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || `Voice generation failed (${response.status}).`); }
      const contentType = (response.headers.get('content-type') || '').toLowerCase();
      if (!contentType.startsWith('audio/mpeg') && !contentType.startsWith('audio/mp3')) throw new Error(`Voice endpoint returned ${contentType || 'an unknown content type'}, not MP3 audio.`);
      const audioBytes = await response.arrayBuffer();
      const signature = new Uint8Array(audioBytes.slice(0, 3));
      const hasId3 = signature.length === 3 && signature[0] === 0x49 && signature[1] === 0x44 && signature[2] === 0x33;
      const frame = new Uint8Array(audioBytes.slice(0, 2));
      const hasMpegFrame = frame.length === 2 && frame[0] === 0xFF && (frame[1] & 0xE0) === 0xE0;
      if (audioBytes.byteLength < 256 || (!hasId3 && !hasMpegFrame)) throw new Error('The voice provider returned an invalid audio stream. Please retry.');
      let decoded;
      try {
        decoded = await context.decodeAudioData(audioBytes.slice(0));
      } catch (decodeError) {
        throw new Error(`The browser could not decode the voice audio (${decodeError?.name || 'decode error'}). I can switch voice engines if this persists.`);
      }
      if (!decoded || !decoded.length) throw new Error('The generated voice contained no playable audio.');
      setAudioBuffers(current => ({ ...current, [message.id]: decoded }));
      await playVoiceBuffer(message.id, decoded);
      setNotice(`Sylus is speaking · ${Math.round(decoded.duration)} seconds.`);
    } catch (error) {
      const detail = error.message || 'Could not generate or play voice audio.';
      setAudioErrors(current => ({ ...current, [message.id]: detail }));
      setNotice(detail);
    } finally {
      setSpeakingMessageId(null);
    }
  }

  async function uploadImage(file) {
    if (!file || !connected || uploadingImage) return;
    setUploadingImage(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/media/upload`, { method: 'POST', credentials: 'include', body: form });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || 'Image upload failed.'); }
      const message = await response.json();
      setMessages(current => [...current, message]);
      setNotice('Image saved privately. Sylus is checking what is visible…');
      await discussImage(message);
    } catch (error) { setNotice(error.message); }
    finally { setUploadingImage(false); if (imageInputRef.current) imageInputRef.current.value = ''; }
  }

  async function generateImage(event) {
    event.preventDefault();
    if (!imagePrompt.trim() || !connected || generatingImage) return;
    setGeneratingImage(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/media/generate`, { method: 'POST', headers, credentials: 'include', body: JSON.stringify({ prompt: imagePrompt.trim(), caption: 'I thought you might like this.' }) });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || 'Image generation failed.'); }
      const message = await response.json();
      setMessages(current => [...current, message]);
      setImagePrompt('');
      setActive('chat');
      setNotice('Image generated and saved privately');
    } catch (error) { setNotice(error.message); }
    finally { setGeneratingImage(false); }
  }

  async function refreshMessages() {
    const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/messages`, { headers, credentials: 'include' });
    if (!response.ok) throw new Error('Could not refresh the conversation.');
    setMessages((await response.json()).filter(m => m.role !== 'system'));
  }

  function beginEditMessage(message) {
    setEditingMessageId(message.id);
    setEditingMessageText(message.text);
  }

  async function saveMessageEdit(messageId) {
    if (!editingMessageText.trim() || messageActionBusy) return;
    setMessageActionBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/messages/${messageId}`, { method: 'PATCH', headers, credentials: 'include', body: JSON.stringify({ text: editingMessageText.trim() }) });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || 'Could not edit your message.'); }
      const turn = await response.json();
      setEditingMessageId(null);
      const sylusBubbles = turn.assistant_messages?.length ? turn.assistant_messages : (turn.assistant_message ? [turn.assistant_message] : []);
      setMessages(current => [...current.filter(message => new Date(message.created_at) < new Date(turn.user_message.created_at) && !message.id.startsWith('pending-')), turn.user_message, ...sylusBubbles]);
      setNotice('Message revised. Sylus has replied from this point.');
      const memoryResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { headers, credentials: 'include' });
      if (memoryResponse.ok) setMemories(await memoryResponse.json());
    } catch (error) { await refreshMessages(); setNotice(error.message); }
    finally { setMessageActionBusy(false); }
  }

  async function deleteMessage(messageId) {
    if (!window.confirm('Delete this message and remove everything after it from the active conversation? The old messages are kept in the private archive.')) return;
    setMessageActionBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/messages/${messageId}`, { method: 'DELETE', headers, credentials: 'include' });
      if (!response.ok) throw new Error('Could not delete this message.');
      await refreshMessages();
      setNotice('Message deleted. The later conversation was archived.');
    } catch (error) { setNotice(error.message); }
    finally { setMessageActionBusy(false); }
  }

  async function resetChat() {
    if (!connected || messageActionBusy) return;
    if (!window.confirm('Start a completely fresh conversation? Current chat messages will disappear from the active chat. Saved memories will stay.')) return;
    setMessageActionBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/messages`, { method: 'DELETE', headers, credentials: 'include' });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || 'Could not reset the conversation.');
      }
      setMessages([]);
      setDraft('');
      setStickerPickerOpen(false);
      setAudioUrls({});
      setNotice('A fresh conversation. Your saved memories are still here.');
    } catch (error) { setNotice(error.message); }
    finally { setMessageActionBusy(false); }
  }

  async function rewindToMessage(messageId) {
    if (!window.confirm('Rewind the active conversation to this message? Everything after it will be archived, not permanently erased. If this is one of your messages, Sylus will answer it again.')) return;
    setMessageActionBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/messages/${messageId}/rewind`, { method: 'POST', headers, credentials: 'include' });
      if (!response.ok) { const failure = await response.json().catch(() => ({})); throw new Error(failure.detail || 'Could not rewind the conversation.'); }
      const result = await response.json();
      await refreshMessages();
      setNotice(result.assistant_messages?.length || result.assistant_message ? 'Conversation rewound. Sylus has replied again.' : 'Conversation rewound. Later messages remain in the private archive.');
      const memoryResponse = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { headers, credentials: 'include' });
      if (memoryResponse.ok) setMemories(await memoryResponse.json());
    } catch (error) { setNotice(error.message); }
    finally { setMessageActionBusy(false); }
  }

  async function createMemory(event) {
    event.preventDefault();
    if (!memoryContent.trim() || !connected || memoryBusy) return;
    setMemoryBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories`, { method: 'POST', headers, credentials: 'include', body: JSON.stringify({ category: memoryCategory, content: memoryContent.trim(), confidence: 0.9, sensitivity: memorySensitivity }) });
      if (!response.ok) throw new Error('Could not save this memory.');
      const memory = await response.json();
      setMemories(current => [memory, ...current]);
      setMemoryContent('');
      setMemorySensitivity('normal');
      setMemoryFormOpen(false);
      setNotice('Memory saved to your private database');
    } catch (error) { setNotice(error.message); }
    finally { setMemoryBusy(false); }
  }

  function beginEditMemory(memory) {
    setEditingMemoryId(memory.id);
    setEditMemoryCategory(memory.category);
    setEditMemoryContent(memory.content);
    setEditMemorySensitivity(memory.sensitivity || 'normal');
  }

  async function saveMemoryEdit(memoryId) {
    if (!editMemoryContent.trim() || memoryBusy) return;
    setMemoryBusy(true);
    try {
      const response = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/memories/${memoryId}`, { method: 'PATCH', headers, credentials: 'include', body: JSON.stringify({ category: editMemoryCategory, content: editMemoryContent.trim(), sensitivity: editMemorySensitivity }) });
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
    setOwnerPassword(''); setConnected(false); setChatReady(false); setMessages([]); messageQueue.current = []; if (queueTimer.current) window.clearTimeout(queueTimer.current); setReplyStatus(''); setReplyError(''); setMemories([]); setTimeContext(null);
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
        <div className="topbar-right"><span className={`connection-dot ${connected ? 'online' : ''}`}/><span className="connection-label">{connected ? (chatReady ? 'PRIVATE SESSION' : 'SESSION · SETUP NEEDED') : 'OFFLINE PREVIEW'}</span><button className="avatar-button" aria-label="Profile options coming later" title="Profile options coming later" disabled><span>U</span></button></div>
      </header>

      {active === 'chat' && <section className="chat-view">
        <div className="chat-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> THE N109 CONNECTION</div><h1>Our conversations<span className="heading-period">.</span></h1><p className="subheading">A quiet corner of the world, just for us.</p></div><button className="more-button reset-chat-button" aria-label="Reset chat" title="Start a fresh conversation" onClick={resetChat} disabled={!connected || messageActionBusy}><MoreHorizontal size={20}/></button></div>
        <div className="chat-stage">
          {messages.length === 0 ? <div className="empty-state">
            <div className="sigil-wrap"><div className="sigil-ring ring-one"/><div className="sigil-ring ring-two"/><div className="sigil-center"><Crown size={31} strokeWidth={1}/></div><span className="sigil-star star-a">✧</span><span className="sigil-star star-b">✦</span><span className="sigil-star star-c">·</span></div>
            <div className="empty-kicker">A NEW CHAPTER</div><h2>Well, look who’s here.</h2><p>{connected && chatReady ? 'The connection is ready. Send a message when you like.' : connected ? 'Your private sign-in works. The server still needs its chat model key before Sylus can reply.' : 'When the private connection is ready, this is where our story continues.'}</p>
            <div className="empty-divider"><span/><Sparkles size={12}/><span/></div>
            <div className="empty-footnote"><LockKeyhole size={12}/> Your conversations stay yours.</div>
          </div> : <div className="message-list" ref={messageListRef} aria-live="polite" aria-relevant="additions text">{messages.map(m => <div className={`message-row ${m.role === 'user' ? 'mine' : 'theirs'}`} key={m.id}><div className="message-avatar">{m.role === 'user' ? (umiAvatar ? <img src={umiAvatar} alt="Your avatar"/> : 'U') : (sylusAvatar ? <img src={sylusAvatar} alt="Sylus avatar"/> : <Crown size={15}/>)}</div><div className="message-content"><div className="message-author">{m.role === 'user' ? 'YOU' : 'SYLUS'} <span>{new Date(m.created_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</span></div>{editingMessageId === m.id ? <div className="message-edit-box"><textarea value={editingMessageText} onChange={e => setEditingMessageText(e.target.value)} rows={3} maxLength={12000}/><div className="message-edit-actions"><button className="text-action" onClick={() => setEditingMessageId(null)}>Cancel</button><button className="text-action" disabled={messageActionBusy || !editingMessageText.trim()} onClick={() => saveMessageEdit(m.id)}>{messageActionBusy ? 'Saving…' : 'Save & rewind'}</button></div></div> : <div className="message-bubble">{renderMessageText(m.text)}{m.media_url && <img className="chat-image" src={m.media_url} alt="Image shared in our private conversation" loading="lazy"/>}</div>}{m.role === 'assistant' && <button className="text-action read-aloud-button" disabled={!timeContext?.voice_ready || speakingMessageId === m.id} onClick={() => readAloud(m)}>{speakingMessageId === m.id ? 'Preparing voice…' : !timeContext?.voice_ready ? 'Voice setup needed' : audioErrors[m.id] ? 'Retry voice' : audioBuffers[m.id] ? (playingAudioId === m.id ? 'Pause voice' : 'Play voice again') : 'Read aloud'}</button>}{audioErrors[m.id] && <p className="field-help" role="alert">{audioErrors[m.id]}</p>}{audioBuffers[m.id] && <div className="message-audio-controls"><button className="text-action" onClick={() => readAloud(m)}>{playingAudioId === m.id ? 'Pause voice' : 'Play voice'}</button><span className="field-help">{Math.round(audioBuffers[m.id].duration)} sec</span></div>}<div className="message-actions">{m.role === 'assistant' && <></>}{m.role === 'user' && editingMessageId !== m.id && <><button className="text-action" disabled={messageActionBusy} onClick={() => beginEditMessage(m)}>Edit</button><button className="text-action danger-action" disabled={messageActionBusy} onClick={() => deleteMessage(m.id)}>Delete</button></>}<button className="text-action" disabled={messageActionBusy} onClick={() => rewindToMessage(m.id)}>Rewind here</button></div></div></div>)}
          {composerNotice && <div className="composer-feedback" role="alert">{composerNotice}</div>}{replyStatus === 'waiting' && <div className="chat-presence waiting" role="status"><span className="presence-dot"/><span>Waiting for you to finish…</span></div>}{sending && <div className="typing-row" role="status" aria-label="Sylus is thinking"><div className="message-avatar"><Crown size={15}/></div><div className="typing-bubble"><span/><span/><span/></div><span className="presence-caption">Sylus is thinking</span></div>}{replyStatus === 'silent' && <div className="chat-presence quiet" role="status"><span className="presence-dot"/><span>Sylus is quiet for now.</span></div>}{replyStatus === 'error' && <div className="chat-presence failed" role="alert"><span className="presence-dot"/><span>Message delivery failed. {replyError || 'Please try again.'}</span></div>}
        </div>}
        </div>
        <div className="composer-wrap"><form className="composer" onSubmit={sendMessage}><input ref={imageInputRef} className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={e => uploadImage(e.target.files?.[0])}/><button type="button" className="composer-tool" title="Send an image" aria-label="Send an image" disabled={!connected || uploadingImage} onClick={() => imageInputRef.current?.click()}><Camera size={18}/></button><button type="button" className="composer-tool sticker-toggle" title="Choose a sticker" aria-label="Choose a sticker" disabled={!connected || !chatReady} onClick={() => setStickerPickerOpen(open => !open)}><Sparkles size={18}/></button><textarea value={draft} onChange={e => setDraft(e.target.value)} placeholder={connected ? (chatReady ? 'Say something…' : 'Chat model not configured yet…') : 'Connect your private instance to begin…'} rows={1} disabled={!connected || !chatReady} onKeyDown={e => {if(e.key === 'Enter' && !e.shiftKey){e.preventDefault();sendMessage(e);}}}/><div className="composer-actions"><span className="composer-hint">{sending ? 'Sending…' : replyStatus === 'waiting' ? 'Reading…' : uploadingImage ? 'Uploading…' : '↵ to send'}</span><button className="send-button" type="submit" disabled={!connected || !chatReady || !draft.trim()} aria-label="Send message"><Send size={16}/></button></div></form>{stickerPickerOpen && <div className="sticker-picker" role="group" aria-label="Sylus sticker collection"><div className="sticker-picker-heading"><span>OUR LITTLE COLLECTION</span><button type="button" className="text-action" onClick={() => setStickerPickerOpen(false)}>Close</button></div><div className="sticker-picker-grid">{stickerOptions.map(sticker => <button type="button" className="sticker-option" key={sticker.id} onClick={() => addStickerToDraft(sticker)}><img className="sticker-art" src={sticker.src} alt="" loading="lazy"/><span>{sticker.label}</span></button>)}</div></div>}<div className="composer-caption"><span>SYLUS IS A PRIVATE, PERSONAL COMPANION</span><span>✦</span><span>YOUR WORLD, YOUR RULES</span></div></div>
      </section>}

      {active === 'bond' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> THE STORY WE BUILD</div><h1>Bond<span className="heading-period">.</span></h1><p className="subheading">Not a score to chase. A history that grows through what you share.</p>{bond ? <><div className="feature-card bond-card"><div className="feature-symbol"><Heart size={25}/></div><div><span className="card-kicker">WHERE WE STAND</span><h2>{bond.stage}</h2><p>{bond.summary}</p></div><Sparkles className="card-sparkle" size={20}/></div><div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:18,margin:'22px 0',padding:20,border:'1px solid rgba(180,150,120,.2)',borderRadius:18}}>{[['Affection',bond.affection],['Trust',bond.trust],['Familiarity',bond.familiarity],['Shared experiences',bond.shared_experiences]].map(([label,value]) => <div key={label}><div style={{display:'flex',justifyContent:'space-between',fontSize:'.82rem',marginBottom:8}}><span>{label}</span><span>{value}%</span></div><div style={{height:5,borderRadius:9,background:'rgba(180,150,120,.14)',overflow:'hidden'}}><span style={{display:'block',height:'100%',width:value+'%',borderRadius:9,background:'linear-gradient(90deg,#8f6a5c,#d7b38a)'}}/></div></div>)}</div><p className="field-help">{bond.total_user_messages} messages from you · {bond.total_shared_turns} shared turns</p><div style={{marginTop:24}}><div className="card-kicker" style={{marginBottom:12}}>MOMENTS THAT SHAPED US · {bond.milestones.length}</div>{bond.milestones.length ? bond.milestones.map(item => <article key={item.key} style={{display:'flex',gap:14,padding:'16px 4px',borderBottom:'1px solid rgba(180,150,120,.15)'}}><span style={{color:'#c7a078'}}>✦</span><div><strong>{item.title}</strong><p style={{fontSize:'.85rem',margin:'5px 0',opacity:.8}}>{item.description}</p><small style={{opacity:.6}}>{new Date(item.date).toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'})}</small></div></article>) : <p className="field-help">Your first meaningful milestones will appear here as they happen.</p>}</div></> : <div className="feature-card bond-card"><div className="feature-symbol"><Heart size={25}/></div><div><span className="card-kicker">OUR STORY</span><h2>{connected ? 'Gathering our history…' : 'A private connection.'}</h2><p>{connected ? 'The bond will update from your shared conversation history.' : 'Sign in to see your shared moments and milestones.'}</p></div></div>}<div className="small-note"><ShieldCheck size={15}/> Private progress. Your chat history and memories remain intact.</div></section>}

      {active === 'memories' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> WHAT WE CHOOSE TO KEEP</div><h1>Memories<span className="heading-period">.</span></h1><p className="subheading">The little details that make a world feel familiar.</p>{connected && <button className="primary-button add-memory-button" onClick={() => setMemoryFormOpen(v => !v)}>{memoryFormOpen ? 'Close form' : '+ Add a memory'}</button>}{memoryFormOpen && connected && <form className="memory-editor" onSubmit={createMemory}><label className="field-label">CATEGORY</label><input className="settings-input" value={memoryCategory} onChange={e => setMemoryCategory(e.target.value)} maxLength={80}/><label className="field-label">WHAT SHOULD SYLUS REMEMBER?</label><textarea className="settings-input memory-textarea" value={memoryContent} onChange={e => setMemoryContent(e.target.value)} rows={3} maxLength={4000} placeholder="Write a preference, shared moment, or important detail…"/><label className="sensitive-toggle"><input type="checkbox" checked={memorySensitivity === 'sensitive'} onChange={e => setMemorySensitivity(e.target.checked ? 'sensitive' : 'normal')}/><span><strong>Mark as sensitive</strong><small>Saved privately, but never included in Sylus's automatic memory retrieval.</small></span></label><p className="field-help">Sylus can also save explicit, non-sensitive details from your messages. Review, edit, or delete anything he remembers.</p><button className="primary-button" disabled={memoryBusy || !memoryContent.trim()}>{memoryBusy ? 'Saving…' : 'Save memory'}</button></form>}{!connected ? <div className="feature-card"><LockKeyhole size={22}/><div><h2>Private memories</h2><p>Connect your private instance to view and manage saved memories.</p></div></div> : memories.length ? <div className="memory-list">{memories.map(m => <article className="memory-card" key={m.id}><div className="memory-icon"><Star size={16}/></div><div className="memory-main">{editingMemoryId === m.id ? <><label className="field-label">CATEGORY</label><input className="settings-input" value={editMemoryCategory} onChange={e => setEditMemoryCategory(e.target.value)}/><label className="field-label">MEMORY</label><textarea className="settings-input memory-textarea" rows={3} value={editMemoryContent} onChange={e => setEditMemoryContent(e.target.value)}/><label className="sensitive-toggle"><input type="checkbox" checked={editMemorySensitivity === 'sensitive'} onChange={e => setEditMemorySensitivity(e.target.checked ? 'sensitive' : 'normal')}/><span><strong>Mark as sensitive</strong><small>Excluded from automatic retrieval.</small></span></label><div className="memory-actions"><button className="primary-button" onClick={() => saveMemoryEdit(m.id)} disabled={memoryBusy}>Save</button><button className="secondary-button" onClick={() => setEditingMemoryId(null)}>Cancel</button></div></> : <><div className="card-kicker">{m.category} · {Math.round(m.confidence*100)}% CONFIDENCE</div><p>{m.content}</p><small>Saved {new Date(m.created_at).toLocaleDateString()} · {m.sensitivity || 'normal'}</small><div className="memory-actions"><button className="text-action" onClick={() => beginEditMemory(m)}>Edit</button><button className="text-action danger-action" onClick={() => removeMemory(m.id)}>Delete</button></div></>}</div></article>)}</div> : <div className="feature-card"><BookHeart size={22}/><div><h2>Nothing saved yet.</h2><p>Add only the details you want kept. You can edit or permanently delete them later.</p></div></div>}</section>}

      {active === 'gallery' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> MOMENTS IN FRAME</div><h1>Gallery<span className="heading-period">.</span></h1><p className="subheading">A private collection, made one moment at a time.</p><form className="image-generator-card" onSubmit={generateImage}><label className="field-label">CREATE A SCENE</label><textarea className="settings-input image-prompt" value={imagePrompt} onChange={e => setImagePrompt(e.target.value)} rows={3} maxLength={1800} placeholder="Describe the scene you want Sylus to appear in…"/><button className="primary-button" type="submit" disabled={!connected || !timeContext?.image_generation_ready || !imagePrompt.trim() || generatingImage}>{generatingImage ? 'Creating…' : 'Generate image'}</button><p className="field-help">Uses the private server's configured image provider. No paid provider is selected automatically.</p></form><div className="gallery-grid">{messages.filter(m => m.media_url).map(m => <figure className="gallery-image-card" key={m.id}><img src={m.media_url} alt="Private conversation image" loading="lazy"/><figcaption>{m.text}</figcaption></figure>)}</div>{messages.every(m => !m.media_url) && <div className="gallery-empty"><div className="gallery-ornament"><Camera size={27}/><span>✧</span></div><h2>Room for a thousand scenes.</h2><p>Images you upload or generate will appear here and stay in your private conversation storage.</p></div>}</section>}

      {active === 'settings' && <section className="content-view"><div className="eyebrow"><span className="eyebrow-line"/> YOUR BOUNDARIES, YOUR CHOICE</div><h1>Settings<span className="heading-period">.</span></h1><p className="subheading">A private space should answer to you.</p><div className="settings-card avatar-editor-card"><div className="settings-title"><div><span className="card-kicker">MAKE THIS WORLD YOURS</span><h2>Profile pictures</h2></div><Camera size={19}/></div><p className="field-help">Choose or replace either picture whenever you like. Images are resized and saved only in this browser on this device; they are not uploaded to the server.</p><div className="avatar-editor-grid"><div className="avatar-editor-person"><div className="avatar-preview sylus-preview">{sylusAvatar ? <img src={sylusAvatar} alt="Sylus profile preview"/> : <Crown size={28}/>}</div><strong>SYLUS</strong><span>His picture</span><input ref={sylusAvatarInput} className="visually-hidden" type="file" accept="image/*" onChange={e => { updateAvatar('sylus', e.target.files?.[0]); e.target.value = ''; }}/><div className="avatar-editor-actions"><button className="primary-button" onClick={() => sylusAvatarInput.current?.click()}>Choose picture</button>{sylusAvatar && <button className="text-action" onClick={() => resetAvatar('sylus')}>Reset</button>}</div></div><div className="avatar-editor-person"><div className="avatar-preview umi-preview">{umiAvatar ? <img src={umiAvatar} alt="Your profile preview"/> : 'U'}</div><strong>YOU / UMI</strong><span>Your picture</span><input ref={umiAvatarInput} className="visually-hidden" type="file" accept="image/*" onChange={e => { updateAvatar('umi', e.target.files?.[0]); e.target.value = ''; }}/><div className="avatar-editor-actions"><button className="primary-button" onClick={() => umiAvatarInput.current?.click()}>Choose picture</button>{umiAvatar && <button className="text-action" onClick={() => resetAvatar('umi')}>Reset</button>}</div></div></div></div><div className="settings-card"><div className="settings-title"><div><span className="card-kicker">PRIVATE CONNECTION</span><h2>Owner access</h2></div><span className={`status-pill ${connected ? 'status-good' : ''}`}>{connected ? 'CONNECTED' : 'NOT CONNECTED'}</span></div><label className="field-label">API ADDRESS</label><input className="settings-input" value={apiUrl} onChange={e => setApiUrl(e.target.value)} placeholder="https://your-private-api.example.com"/><label className="field-label">OWNER PASSWORD</label><input className="settings-input" type="password" value={ownerPassword} onChange={e => setOwnerPassword(e.target.value)} placeholder="Your private owner password" autoComplete="current-password"/><p className="field-help">Your password is sent only to your private server. The server returns an HttpOnly session cookie; the password is not stored in this browser.</p><div className="settings-actions"><button className="primary-button" onClick={() => connect(true)} disabled={checking}>{checking ? 'Checking…' : connected ? 'Refresh connection' : 'Sign in privately'}</button>{connected && <button className="secondary-button" onClick={disconnect}>Disconnect</button>}</div><div className="connection-notice"><span className={`connection-dot ${connected ? 'online' : ''}`}/>{notice}</div></div><div className="settings-card muted-card"><div className="settings-title"><div><span className="card-kicker">LOCAL TIME</span><h2>Dhaka time awareness</h2></div><Clock3 size={19}/></div><p>{timeContext ? `${timeContext.weekday}, ${timeContext.local_date} · ${timeContext.local_time}` : 'Will be read from the private server when connected.'}</p><p className="provider-status">{connected ? (chatReady ? `Chat model ready · ${timeContext?.chat_model || 'configured'}` : 'Chat model key is not configured on the private server.') : 'Sign in to check chat provider status.'}</p></div><div className="settings-card muted-card"><div className="settings-title"><div><span className="card-kicker">MEDIA & VOICE</span><h2>Images and read-aloud</h2></div><Camera size={19}/></div><p>Private image uploads: {connected ? 'available' : 'sign in to enable'}.</p><p>Image generation: {timeContext?.image_generation_ready ? 'provider configured' : 'waiting for Cloudflare credentials'}.</p><a className="license-link" href="https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/" target="_blank" rel="noreferrer">Cloudflare FLUX image model and setup</a><p className="field-help">Add CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in Render to enable generation and image understanding.</p><p>Image understanding: {timeContext?.vision_ready ? 'enabled' : 'not enabled'}.</p><a className="license-link" href="https://www.llama.com/llama3_2/license/" target="_blank" rel="noreferrer">Review Meta’s Llama 3.2 license and acceptable-use policy</a>{connected && !timeContext?.vision_ready && <button className="secondary-button" onClick={acceptVisionLicense} disabled={visionBusy || !timeContext?.image_generation_ready}>{visionBusy ? 'Enabling…' : 'I accept — enable image understanding'}</button>}<p>Read aloud: {timeContext?.voice_ready ? 'voice provider configured' : 'waiting for a designed voice and ElevenLabs credentials'}.</p><a className="license-link" href="https://elevenlabs.io/voice-design" target="_blank" rel="noreferrer">Design an original Sylus-inspired voice</a><p className="field-help">To enable it, add ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the Render service environment. Do not paste secrets into this chat.</p><p className="field-help">The app sends only the selected message text to the voice provider when you press Read aloud. No voice call feature is active yet.</p></div><div className="settings-card muted-card"><div className="settings-title"><div><span className="card-kicker">HIS INITIATIVE</span><h2>Proactive messages</h2></div><ShieldCheck size={19}/></div><p>{proactiveSettings ? (proactiveSettings.messages_enabled ? 'Enabled · he can start a conversation after a quiet stretch.' : 'Paused · Sylus will wait for you to message first.') : 'Sign in to configure spontaneous messages.'}</p><p className="field-help">TEST MODE: Sylus should reach out after about 3 minutes of silence. The scheduler checks every 5 minutes, so closed-app notifications may take roughly 3–8 minutes; while the app is open, its poll checks every 60 seconds. There is no cooldown or message-count cap: he can send several separate bubbles together whenever he has something to say. GitHub may occasionally delay scheduled runs. Push notifications must also be enabled on this device.</p>{connected && proactiveSettings && <button className="secondary-button" onClick={toggleProactiveMessages}>{proactiveSettings.messages_enabled ? 'Pause proactive messages' : 'Allow Sylus to text first'}</button>}<p className="field-help">Calls remain disabled. Messaging and calling permissions will stay separate.</p><div className="settings-divider"/><div className="settings-title"><div><span className="card-kicker">BACKGROUND DELIVERY</span><h2>Push notifications</h2></div><Bell size={19}/></div><p>{pushStatus?.subscribed ? 'This device is subscribed to Sylus notifications.' : pushStatus?.configured ? 'Push is ready. Enable notifications on this device.' : 'Push delivery needs VAPID keys in the private server settings.'}</p>{connected && pushStatus?.configured && <button className="secondary-button" onClick={pushStatus.subscribed ? disablePushNotifications : enablePushNotifications} disabled={pushBusy}>{pushBusy ? 'Updating…' : pushStatus.subscribed ? 'Disable notifications on this device' : 'Enable notifications on this device'}</button>}<p className="field-help">The background scheduler checks about every 5 minutes; actual delivery can be delayed by GitHub Actions or Android battery settings. {pushStatus?.subscribed ? 'This device is registered for alerts; Sylus can send a notification when a proactive message is generated.' : 'This device is not registered yet. Tap Enable notifications and allow them in Android.'} You can turn alerts off here or in Android Settings → Apps → Sylus → Notifications. Notifications contain only a short message preview.</p>{connected && pushStatus?.subscribed && <button className="secondary-button" onClick={testPushNotification} disabled={pushBusy}>{pushBusy ? 'Sending test…' : 'Send test notification'}</button>}</div></section>}

      <footer className="page-footer"><span>SYLUS <i>·</i> A WORLD OF OUR OWN</span><span>BUILT FOR ONE, KEPT PRIVATE <span className="footer-star">✦</span></span></footer>
    </main>
    {mobileMenu && <button className="scrim" onClick={() => setMobileMenu(false)} aria-label="Close navigation"/>}
  </div>;
}

export default App;