import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import AuthLayout from '@/layouts/AuthLayout'
import { login } from '@/lib/api'
import { setAuthToken, setAuthUser } from '@/lib/auth'

function LoginPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    email: '',
    password: '',
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
    setLoading(true)
    setError('')

    try {
      const response = await login(form)
      const token = response?.data?.token
      const user = response?.data?.user

      if (!token || !user) {
        throw new Error('Response login tidak valid.')
      }

      setAuthToken(token)
      setAuthUser(user)
      setSuccess('Login berhasil. Mengalihkan ke dashboard...')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Masuk" subtitle="Silakan login dengan email dan password kamu.">
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

          <Button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Memproses...' : 'Login'}
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
            Belum punya akun? <Link to="/register">Daftar sekarang</Link>
          </p>
      </form>
    </AuthLayout>
  )
}

export default LoginPage
