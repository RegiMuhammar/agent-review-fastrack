import { useState } from 'react'
import { Button } from '@/components/ui/button'
import './App.css'

function App() {
  const [form, setForm] = useState({
    email: '',
    password: '',
  })
  const [submitted, setSubmitted] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({
      ...current,
      [name]: value,
    }))
    setSubmitted(false)
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setSubmitted(true)
  }

  return (
    <main className="login-shell">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-head">
          <h1 id="login-title">Masuk</h1>
          <p>Silakan login dengan email dan password kamu.</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            placeholder="nama@email.com"
            autoComplete="email"
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />

          <Button type="submit" className="login-submit">
            Login
          </Button>

          {submitted && (
            <p className="login-status" role="status">
              Login dikirim untuk {form.email}
            </p>
          )}
        </form>
      </section>
    </main>
  )
}

export default App
