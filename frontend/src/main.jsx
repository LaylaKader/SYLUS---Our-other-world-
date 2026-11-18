import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles.css';

class StartupErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('SYLUS render failed:', error, info?.componentStack || '');
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24, background: '#100e13', color: '#eee9ef', fontFamily: 'system-ui, sans-serif' }}>
          <section style={{ maxWidth: 560, width: '100%', padding: 24, border: '1px solid #6d4658', borderRadius: 14, background: '#17141b' }}>
            <p style={{ color: '#c9a875', letterSpacing: 2, fontSize: 11 }}>SYLUS · STARTUP DIAGNOSTIC</p>
            <h1 style={{ fontSize: 24 }}>The interface could not finish starting.</h1>
            <p style={{ color: '#c8bacb', lineHeight: 1.6 }}>The server and database may still be available. This message captures a frontend rendering error so it can be fixed without touching your saved data.</p>
            <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', padding: 14, borderRadius: 8, background: '#100e13', color: '#f0c6d1', fontSize: 12 }}>{String(this.state.error?.message || this.state.error)}</pre>
            <button onClick={() => window.location.reload()} style={{ padding: '10px 16px', borderRadius: 8, border: '1px solid #9b7182', background: '#6f344a', color: 'white' }}>Reload SYLUS</button>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}

function showFatalStartupError(message) {
  const root = document.getElementById('root');
  if (!root) return;
  const panel = document.createElement('main');
  panel.style.cssText = 'min-height:100vh;display:grid;place-items:center;padding:24px;background:#100e13;color:#eee9ef;font:14px system-ui,sans-serif';
  const section = document.createElement('section');
  section.style.cssText = 'max-width:560px;width:100%;padding:24px;border:1px solid #6d4658;border-radius:14px;background:#17141b';
  const title = document.createElement('h1');
  title.textContent = 'SYLUS could not start';
  title.style.cssText = 'font-size:24px';
  const detail = document.createElement('pre');
  detail.textContent = message;
  detail.style.cssText = 'white-space:pre-wrap;overflow-wrap:anywhere;padding:14px;border-radius:8px;background:#100e13;color:#f0c6d1;font-size:12px';
  const note = document.createElement('p');
  note.textContent = 'This is a frontend startup error. Your database has not been changed.';
  note.style.cssText = 'color:#c8bacb;line-height:1.6';
  section.append(title, note, detail);
  panel.append(section);
  root.replaceChildren(panel);
}

// Runtime errors must never replace the mounted app. In particular, a failed
// image decode or a rejected background request must not blank the Settings page.
// React rendering failures are handled by StartupErrorBoundary above.
window.addEventListener('error', event => {
  if (event.target && event.target !== window) {
    console.warn('SYLUS resource failed to load:', event.target?.src || event.target?.href || event.target);
    return;
  }
  console.error('SYLUS uncaught browser error:', event.error || event.message);
});
window.addEventListener('unhandledrejection', event => {
  console.error('SYLUS unhandled promise rejection (app kept mounted):', event.reason);
});

const rootElement = document.getElementById('root');
if (!rootElement) {
  showFatalStartupError('The HTML page is missing the #root mount element.');
} else {
  try {
    createRoot(rootElement).render(
      <React.StrictMode>
        <StartupErrorBoundary><App /></StartupErrorBoundary>
      </React.StrictMode>
    );
  } catch (error) {
    console.error('SYLUS failed before React could mount:', error);
    showFatalStartupError(error?.stack || error?.message || String(error));
  }
}

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' })
      .then(registration => registration.update().catch(error => {
        console.warn('SYLUS service worker update check failed:', error);
      }))
      .catch(error => {
        console.warn('SYLUS offline support could not be registered:', error);
      });
  });
}
