import { useEffect, useState } from 'react'

type HealthResponse = {
  frontend: string
  backend: string
  database: string
  databaseName?: string | null
}

const defaultHealth: HealthResponse = {
  frontend: 'active',
  backend: 'connected',
  database: 'connected',
  databaseName: null,
}

function App() {
  const [health, setHealth] = useState<HealthResponse>(defaultHealth)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const statusLabel = status === 'ready' ? 'Operational' : status === 'loading' ? 'Checking' : 'Attention'

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const response = await fetch('/api/health')
        if (!response.ok) {
          throw new Error('Health request failed')
        }

        const data = (await response.json()) as HealthResponse
        setHealth({ ...defaultHealth, ...data })
        setStatus('ready')
      } catch {
        setHealth({
          frontend: 'active',
          backend: 'disconnected',
          database: 'disconnected',
          databaseName: null,
        })
        setStatus('error')
      }
    }

    void loadHealth()
  }, [])

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Starter Environment</p>
        <h1>Boilerplate Dashboard</h1>
        <p className="subtitle">React frontend, Python backend, and database wiring at a glance.</p>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>System Health</h2>
          <span className={`status-badge status-${status}`}>{statusLabel}</span>
        </div>

        <div className="health-grid">
          <article className="health-card">
            <p className="label">Frontend</p>
            <p className="value">{health.frontend}</p>
          </article>

          <article className="health-card">
            <p className="label">Backend</p>
            <p className="value">{health.backend}</p>
          </article>

          <article className="health-card">
            <p className="label">Database</p>
            <p className="value">{health.database}</p>
          </article>
        </div>

        <p className="db-meta">{health.databaseName ? `Connected DB: ${health.databaseName}` : 'Connected DB: not set'}</p>
      </section>
    </main>
  )
}

export default App
