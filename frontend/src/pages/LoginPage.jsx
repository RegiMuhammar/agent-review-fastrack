import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

function LoginPage() {
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
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="auth-head">
          <h1 id="login-title">Masuk</h1>
          <p>Silakan login dengan email dan password kamu.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
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
            minLength={8}
            required
          />

          <Button type="submit" className="auth-submit">
            Login
          </Button>

          {submitted && (
            <p className="auth-status" role="status">
              Login dikirim untuk {form.email}
            </p>
          )}

          <p className="form-note">
            Belum punya akun? <Link to="/register">Daftar sekarang</Link>
          </p>
        </form>
      </section>
    </main>
  )
}

export default LoginPage
