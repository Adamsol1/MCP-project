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
