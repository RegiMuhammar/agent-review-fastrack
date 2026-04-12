import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

function RegisterPage() {
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({
      ...current,
      [name]: value,
    }))
    setSubmitted(false)
    setError('')
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (form.password !== form.confirmPassword) {
      setError('Password dan konfirmasi password harus sama.')
      setSubmitted(false)
      return
    }

    setError('')
    setSubmitted(true)
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="register-title">
        <div className="auth-head">
          <h1 id="register-title">Daftar Akun</h1>
          <p>Buat akun baru untuk mulai menggunakan aplikasi.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="name">Nama Lengkap</label>
          <input
            id="name"
            name="name"
            type="text"
            value={form.name}
            onChange={handleChange}
            placeholder="Nama kamu"
            autoComplete="name"
            required
          />

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
            autoComplete="new-password"
            minLength={8}
            required
          />

          <label htmlFor="confirmPassword">Konfirmasi Password</label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            value={form.confirmPassword}
            onChange={handleChange}
            placeholder="••••••••"
            autoComplete="new-password"
            minLength={8}
            required
          />

          <Button type="submit" className="auth-submit">
            Daftar
          </Button>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          {submitted && (
            <p className="auth-status" role="status">
              Registrasi dikirim untuk {form.name} ({form.email})
            </p>
          )}

          <p className="form-note">
            Sudah punya akun? <Link to="/login">Masuk di sini</Link>
          </p>
        </form>
      </section>
    </main>
  )
}

export default RegisterPage
