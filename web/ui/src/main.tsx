import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

// Detect headless automation (Playwright/Chromium screenshot harness). These
// renderers freeze CSS transitions and rAF mid-flight, capturing a wrong frame.
// When detected, snap transitions/animations to final state (see index.css) so
// screenshots are truthful. Real users never hit this path.
const isAutomation =
  typeof navigator !== 'undefined' &&
  (navigator.webdriver || /\bHeadless/.test(navigator.userAgent));
if (isAutomation) {
  document.documentElement.setAttribute('data-no-anim', '');
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
