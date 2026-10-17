import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { startAppearance } from './lib/appearance.ts'
import { sendTokenWithWrites } from './lib/launchToken.ts'
import { PANEL_WINDOW } from './lib/panelWindows.ts'
import { PanelWindow } from './components/dock/PanelWindow.tsx'

startAppearance()
sendTokenWithWrites()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      {PANEL_WINDOW ? <PanelWindow panel={PANEL_WINDOW} /> : <App />}
    </ErrorBoundary>
  </StrictMode>,
)
