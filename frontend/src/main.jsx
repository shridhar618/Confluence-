import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0d1220',
            color: '#e2e8f0',
            border: '1px solid rgba(255,255,255,0.08)',
            fontFamily: 'Syne, sans-serif',
            fontSize: '14px',
          },
          success: { iconTheme: { primary: '#06d6a0', secondary: '#080c14' } },
          error: { iconTheme: { primary: '#ff4d6d', secondary: '#080c14' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
