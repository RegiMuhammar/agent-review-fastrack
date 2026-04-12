import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { getMe, logout } from '@/lib/api'
import { clearAuthSession, getAuthToken, getAuthUser, setAuthUser } from '@/lib/auth'

function DashboardPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState(getAuthUser())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [loggingOut, setLoggingOut] = useState(false)

  useEffect(() => {
    const loadProfile = async () => {
      const token = getAuthToken()

      if (!token) {
        navigate('/login', { replace: true })
        return
      }

      try {
        const response = await getMe(token)
        const currentUser = response?.data?.user

        if (!currentUser) {
          throw new Error('Data user tidak ditemukan.')
        }

        setUser(currentUser)
        setAuthUser(currentUser)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadProfile()
  }, [navigate])

  const handleLogout = async () => {
    const token = getAuthToken()
    setLoggingOut(true)

    try {
      if (token) {
        await logout(token)
      }
    } finally {
      clearAuthSession()
      navigate('/login', { replace: true })
    }
  }

  return (
    <main className="dashboard-shell">
      <section className="dashboard-card">
        <div className="dashboard-head">
          <h1>Dashboard</h1>
          <p>Selamat datang di halaman dashboard sederhana.</p>
        </div>

        {loading && <p className="dashboard-info">Memuat data user...</p>}

        {!loading && error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {!loading && !error && user && (
          <div className="dashboard-user">
            <p>
              <strong>Nama:</strong> {user.name}
            </p>
            <p>
              <strong>Email:</strong> {user.email}
            </p>
          </div>
        )}

        <Button
          type="button"
          variant="destructive"
          className="dashboard-logout"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          {loggingOut ? 'Keluar...' : 'Logout'}
        </Button>
      </section>
    </main>
  )
}

export default DashboardPage
