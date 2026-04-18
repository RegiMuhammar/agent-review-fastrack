import { useState } from 'react'
import { History, LayoutDashboard, LogOut, NotebookPen } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import AlertPopup from '@/components/ui/alert-popup'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/api'
import { clearAuthSession, getAuthToken } from '@/lib/auth'

function sidebarLinkClassName({ isActive }) {
  const baseClassName = 'flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors'

  if (isActive) {
    return `${baseClassName} bg-[#5E74C9] text-white shadow-sm`
  }

  return `${baseClassName} text-[#5E74C9] hover:bg-[#5E74C9]/10`
}

function ProtectedLayout() {
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [isLogoutPopupOpen, setIsLogoutPopupOpen] = useState(false)

  async function confirmLogout() {
    const token = getAuthToken()
    setIsLoggingOut(true)

    try {
      if (token) {
        await logout(token)
      }
    } catch {
      // Even if API logout fails, local session should still be cleared.
    } finally {
      clearAuthSession()
      navigate('/', { replace: true })
      setIsLoggingOut(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-[linear-gradient(120deg,#eaf0ff_0%,#f6f8ff_45%,#ffffff_100%)]">
      <AlertPopup
        open={isLogoutPopupOpen}
        title="Keluar dari akun?"
        description="Sesi Anda akan diakhiri dan diarahkan ke halaman utama."
        variant="warning"
        confirmLabel={isLoggingOut ? 'Keluar...' : 'Ya, Logout'}
        cancelLabel="Batal"
        onCancel={() => {
          if (!isLoggingOut) {
            setIsLogoutPopupOpen(false)
          }
        }}
        onConfirm={async () => {
          if (isLoggingOut) {
            return
          }

          setIsLogoutPopupOpen(false)
          await confirmLogout()
        }}
      />

      <div className="grid min-h-screen w-full md:grid-cols-[260px_1fr]">
        <aside className="flex flex-col border-b border-[#5E74C9]/16 bg-white/85 p-4 backdrop-blur md:border-b-0 md:border-r md:p-6">
          <div className="mb-5">
            <p className="text-xs font-semibold tracking-[0.16em] text-[#5E74C9]">JURNAL AI FASTTRACK</p>
          </div>

          <nav className="grid gap-2">
            <NavLink to="/dashboard" className={sidebarLinkClassName} end>
              <LayoutDashboard className="size-4" />
              Dashboard
            </NavLink>
            <NavLink to="/review-jurnal" className={sidebarLinkClassName}>
              <NotebookPen className="size-4" />
              Review Jurnal
            </NavLink>
            <NavLink to="/history-jurnal" className={sidebarLinkClassName}>
              <History className="size-4" />
              History Jurnal
            </NavLink>
          </nav>

          <div className="mt-5 md:mt-auto">
            <Button
              type="button"
              onClick={() => setIsLogoutPopupOpen(true)}
              disabled={isLoggingOut}
              className="h-10 w-full bg-[#5E74C9] text-white hover:bg-[#5166B8]"
            >
              <LogOut className="mr-1 size-4" />
              {isLoggingOut ? 'Keluar...' : 'Logout'}
            </Button>
          </div>
        </aside>

        <section className="w-full p-4 sm:p-6 md:p-8">
          <Outlet />
        </section>
      </div>
    </div>
  )
}

export default ProtectedLayout
