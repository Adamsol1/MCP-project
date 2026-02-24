/**
 * Application entry point.
 *
 * Mounts the React component tree into the #root element defined in index.html.
 *
 * Provider order matters — outermost providers are available to every component
 * below them. ToastProvider wraps ConversationProvider so that conversation-level
 * code can trigger toast notifications without a circular dependency:
 *
 *   StrictMode
 *   └─ ToastProvider              (toast state & helpers available everywhere)
 *      └─ ConversationProvider    (conversation state can call useToast safely)
 *         └─ App
 *
 * StrictMode causes React to intentionally render each component twice in
 * development to surface bugs from impure render functions or missing effect
 * cleanup. It has no effect in production builds.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { ToastProvider } from './contexts/ToastContext'
import { ConversationProvider } from './contexts/ConversationContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastProvider>
      <ConversationProvider>
        <App />
      </ConversationProvider>
    </ToastProvider>
  </StrictMode>,
)
