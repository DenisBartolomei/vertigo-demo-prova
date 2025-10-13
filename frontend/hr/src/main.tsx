import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { App } from './routes/App'
import { Positions } from './routes/Positions'
import { InterviewSetup } from './routes/InterviewSetup'
import { Candidati } from './routes/Candidati'
import { NuovaSessione } from './routes/NuovaSessione'
import { UserManagement } from './routes/UserManagement'
import { Dashboard } from './routes/Dashboard'
import { Login } from './routes/Login'
import { ErrorBoundary } from './components/ErrorBoundary'

const router = createBrowserRouter([
  { path: '/', element: <Login /> },
  {
    path: '/app',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> }, // Default route for /app
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'positions', element: <Positions /> },
      { path: 'setup-colloqui', element: <InterviewSetup /> },
      { path: 'candidati', element: <Candidati /> },
      { path: 'nuova-sessione', element: <NuovaSessione /> },
      { path: 'users', element: <UserManagement /> },
    ],
  },
  {
    path: '*',
    element: (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        padding: '20px',
        textAlign: 'center',
        background: 'linear-gradient(135deg, #F3F0FF 0%, #FDF2F8 100%)'
      }}>
        <div style={{ 
          background: 'white',
          padding: '40px',
          borderRadius: '16px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
          maxWidth: '500px'
        }}>
          <h1 style={{ 
            color: '#8B5CF6', 
            fontSize: '32px', 
            marginBottom: '16px',
            fontWeight: '700'
          }}>
            Pagina Non Trovata
          </h1>
          <p style={{ 
            color: '#6B7280', 
            fontSize: '18px', 
            marginBottom: '24px' 
          }}>
            La pagina che stai cercando non esiste.
          </p>
          <button 
            onClick={() => window.location.href = '/app'}
            style={{
              background: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            🏠 Torna alla Dashboard
          </button>
        </div>
      </div>
    )
  }
])

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  </React.StrictMode>
)


