import { History, LayoutDashboard, NotebookPen } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

function sidebarLinkClassName({ isActive }) {
  const baseClassName = 'flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors'

  if (isActive) {
    return `${baseClassName} bg-[#5E74C9] text-white shadow-sm`
  }

  return `${baseClassName} text-[#5E74C9] hover:bg-[#5E74C9]/10`
}

function ProtectedLayout() {
  return (
    <div className="min-h-screen w-full bg-[linear-gradient(120deg,#eaf0ff_0%,#f6f8ff_45%,#ffffff_100%)]">
      <div className="grid min-h-screen w-full md:grid-cols-[260px_1fr]">
        <aside className="border-b border-[#5E74C9]/16 bg-white/85 p-4 backdrop-blur md:border-b-0 md:border-r md:p-6">
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
        </aside>

        <section className="w-full p-4 sm:p-6 md:p-8">
          <Outlet />
        </section>
      </div>
    </div>
  )
}

export default ProtectedLayout
