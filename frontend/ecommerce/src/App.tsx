import { useEffect, useState } from 'react'
import './App.css'

const API = import.meta.env.VITE_API_URL

interface Product {
  id: string
  name: string
  price: string
  description: string
}

interface PaginatedResponse {
  count: number
  results: Product[]
}

type Status = 'loading' | 'success' | 'error'

function App() {
  const [products, setProducts] = useState<Product[]>([])
  const [status, setStatus] = useState<Status>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/products/`)
      .then((r) => {
        if (!r.ok) throw new Error(`Server returned ${r.status}`)
        return r.json() as Promise<PaginatedResponse>
      })
      .then((data) => {
        setProducts(data.results)
        setStatus('success')
      })
      .catch((e: Error) => {
        setError(e.message)
        setStatus('error')
      })
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Products</h1>
      <p style={{ color: '#888', marginBottom: '1.5rem' }}>
        Fetching from <code>{API}/api/products/</code>
      </p>

      {status === 'loading' && <p>Loading...</p>}

      {status === 'error' && (
        <p style={{ color: 'red' }}>
          Failed to fetch: {error}
        </p>
      )}

      {status === 'success' && products.length === 0 && (
        <p style={{ color: '#888' }}>
          No products yet. Add some via the admin or API.
        </p>
      )}

      {status === 'success' && products.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '1rem' }}>
          {products.map((p) => (
            <li
              key={p.id}
              style={{
                border: '1px solid #333',
                borderRadius: '8px',
                padding: '1rem',
              }}
            >
              <strong>{p.name}</strong>
              <span style={{ float: 'right', color: '#4ade80' }}>
                ₦{Number(p.price).toLocaleString()}
              </span>
              <p style={{ margin: '0.5rem 0 0', color: '#aaa', fontSize: '0.9rem' }}>
                {p.description}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default App
