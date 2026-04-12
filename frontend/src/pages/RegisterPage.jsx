import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import AuthLayout from '@/layouts/AuthLayout'
import { register } from '@/lib/api'
import { setAuthToken, setAuthUser } from '@/lib/auth'

function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({
      ...current,
      [name]: value,
    }))
    setSuccess('')
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (form.password !== form.confirmPassword) {
      setError('Password dan konfirmasi password harus sama.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await register({
        name: form.name,
        email: form.email,
        password: form.password,
      })
      const token = response?.data?.token
      const user = response?.data?.user

      if (!token || !user) {
        throw new Error('Response register tidak valid.')
      }

      setAuthToken(token)
      setAuthUser(user)
      setSuccess('Registrasi berhasil. Mengalihkan ke dashboard...')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Daftar Akun"
      subtitle="Buat akun baru untuk mulai menggunakan aplikasi."
    >
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

          <Button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Memproses...' : 'Daftar'}
          </Button>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="auth-status" role="status">
              {success}
            </p>
          )}

          <p className="form-note">
            Sudah punya akun? <Link to="/login">Masuk di sini</Link>
          </p>
      </form>
    </AuthLayout>
  )
}

export default RegisterPage
