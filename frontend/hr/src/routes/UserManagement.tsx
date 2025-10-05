import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

type User = {
  _id: string
  email: string
  name: string
  role: string
  created_at: string
  last_login: string | null
}

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createForm, setCreateForm] = useState({
    email: '',
    password: '',
    name: '',
    role: 'hr'
  })
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const token = localStorage.getItem('hr_jwt')

  async function loadUsers() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/users`, { 
        headers: { Authorization: `Bearer ${token}` } 
      })
      if (res.status === 401) {
        localStorage.removeItem('hr_jwt')
        window.location.href = '/login'
        return
      }
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users || [])
      } else {
        console.error('Failed to load users:', res.statusText)
      }
    } catch (error) {
      console.error('Error loading users:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadCurrentUser() {
    try {
      const res = await fetch(`${API_BASE}/user/info`, { 
        headers: { Authorization: `Bearer ${token}` } 
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentUser(data)
        setIsAdmin(data?.role === 'admin')
        console.log('Current user loaded:', data, 'Is admin:', data?.role === 'admin')
      }
    } catch (error) {
      console.error('Error loading current user:', error)
    }
  }

  useEffect(() => { 
    loadUsers()
    loadCurrentUser()
  }, [])

  async function createUser() {
    if (!createForm.email || !createForm.password || !createForm.name) {
      alert('Compila tutti i campi')
      return
    }

    try {
      const res = await fetch(`${API_BASE}/users`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify(createForm)
      })

      if (res.ok) {
        alert('Utente creato con successo!')
        setCreateForm({ email: '', password: '', name: '', role: 'hr' })
        setShowCreateForm(false)
        await loadUsers()
      } else {
        const error = await res.json()
        alert(`Errore: ${error.detail || 'Impossibile creare l\'utente'}`)
      }
    } catch (error) {
      alert('Errore durante la creazione dell\'utente')
    }
  }

  async function deactivateUser(userId: string) {
    if (!confirm('Sei sicuro di voler disattivare questo utente?')) {
      return
    }

    try {
      const res = await fetch(`${API_BASE}/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.ok) {
        alert('Utente disattivato con successo!')
        await loadUsers()
      } else {
        const error = await res.json()
        alert(`Errore: ${error.detail || 'Impossibile disattivare l\'utente'}`)
      }
    } catch (error) {
      alert('Errore durante la disattivazione dell\'utente')
    }
  }

  return (
    <div className="container" style={{ display: 'grid', gap: '32px' }}>
      <div>
        <h2>Gestione Utenti</h2>
        <p className="muted">Gestisci gli utenti e il loro accesso al sistema di reclutamento della tua organizzazione.</p>
      </div>

      {/* Debug info for admin detection */}
      {import.meta.env.DEV && (
        <div style={{ 
          padding: '12px', 
          background: '#F3F4F6', 
          borderRadius: '8px', 
          fontSize: '12px',
          color: '#6B7280'
        }}>
          Debug: isAdmin = {isAdmin.toString()}, currentUser = {JSON.stringify(currentUser)}
        </div>
      )}

      {/* Admin role warning */}
      {currentUser && currentUser.role !== 'admin' && (
        <div style={{ 
          padding: '16px', 
          background: '#FEF3C7', 
          borderRadius: '8px', 
          border: '1px solid #F59E0B',
          color: '#92400E'
        }}>
          <div style={{ fontWeight: '600', marginBottom: '8px' }}>⚠️ Accesso Limitato</div>
          <div style={{ fontSize: '14px' }}>
            Solo gli amministratori possono creare e gestire utenti. 
            Il tuo ruolo attuale è: <strong>{currentUser.role === 'hr' ? 'Utente HR' : currentUser.role}</strong>
          </div>
        </div>
      )}

      {/* Create User Form */}
      {(isAdmin || currentUser?.role === 'admin') && (
        <div className="card fade-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              borderRadius: '50%', 
              background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '18px'
            }}>
              👥
            </div>
            <h3>Aggiungi Nuovo Utente</h3>
          </div>

          {!showCreateForm ? (
            <button 
              onClick={() => setShowCreateForm(true)}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              ➕ Aggiungi Nuovo Utente
            </button>
          ) : (
            <div style={{ display: 'grid', gap: '20px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
                  Indirizzo Email
                </label>
                <input 
                  type="email"
                  placeholder="utente@azienda.com" 
                  value={createForm.email} 
                  onChange={e => setCreateForm(prev => ({ ...prev, email: e.target.value }))} 
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
                  Nome Completo
                </label>
                <input 
                  placeholder="Mario Rossi" 
                  value={createForm.name} 
                  onChange={e => setCreateForm(prev => ({ ...prev, name: e.target.value }))} 
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
                  Ruolo
                </label>
                <select 
                  value={createForm.role} 
                  onChange={e => setCreateForm(prev => ({ ...prev, role: e.target.value }))}
                >
                  <option value="hr">Utente HR</option>
                  <option value="admin">Amministratore</option>
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
                  Password
                </label>
                <input 
                  type="password"
                  placeholder="Inserisci password" 
                  value={createForm.password} 
                  onChange={e => setCreateForm(prev => ({ ...prev, password: e.target.value }))} 
                />
              </div>
              
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  onClick={createUser}
                  style={{ flex: 1, justifyContent: 'center' }}
                >
                  ✅ Crea Utente
                </button>
                <button 
                  onClick={() => {
                    setShowCreateForm(false)
                    setCreateForm({ email: '', password: '', name: '', role: 'hr' })
                  }}
                  style={{ flex: 1, justifyContent: 'center', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                >
                  ❌ Annulla
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Users List */}
      <div className="card fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            borderRadius: '50%', 
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '18px'
          }}>
            📋
          </div>
          <h3>Utenti Attuali</h3>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
            Caricamento utenti...
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {users.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px', 
                color: 'var(--text-muted)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>👥</div>
                <div style={{ fontSize: '18px', marginBottom: '8px' }}>Nessun utente trovato</div>
                <div>Aggiungi il tuo primo utente per iniziare</div>
              </div>
            ) : (
              users.map((user) => (
                <div key={user._id} className="card" style={{ 
                  display: 'grid', 
                  gridTemplateColumns: '1fr auto auto', 
                  gap: '16px', 
                  alignItems: 'center',
                  transition: 'all 0.2s ease'
                }}>
                  <div>
                    <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '4px' }}>
                      {user.name}
                    </div>
                    <div className="muted" style={{ marginBottom: '4px' }}>
                      {user.email}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Ruolo: {user.role === 'admin' ? 'Amministratore' : 'Utente HR'} • Creato: {new Date(user.created_at).toLocaleDateString('it-IT')}
                    </div>
                  </div>
                  
                  <div style={{ 
                    padding: '4px 12px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: '500',
                    background: user.role === 'admin' ? '#D1FAE5' : '#DBEAFE',
                    color: user.role === 'admin' ? '#065F46' : '#1E40AF'
                  }}>
                    {user.role === 'admin' ? 'ADMIN' : 'HR'}
                  </div>
                  
                  {(isAdmin || currentUser?.role === 'admin') && user._id !== currentUser?.id && (
                    <button
                      onClick={() => deactivateUser(user._id)}
                      style={{ 
                        fontSize: '12px', 
                        padding: '8px 12px',
                        background: '#EF4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        fontWeight: '500'
                      }}
                      title="Disattiva utente"
                    >
                      🗑️ Disattiva
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
