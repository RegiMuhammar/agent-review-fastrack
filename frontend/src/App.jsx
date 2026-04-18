import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'

import ProtectedLayout from '@/components/layout/ProtectedLayout'
import { getAuthToken } from '@/lib/auth'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import AnalisisJurnalPage from '@/pages/dashboard/AnalisisJurnalPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import HistoryJurnalPage from '@/pages/dashboard/HistoryJurnalPage'
import ReviewJurnalPage from '@/pages/dashboard/ReviewJurnalPage'
import HomePage from '@/pages/public/HomePage'

function ProtectedRoute() {
  const token = getAuthToken()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

function GuestRoute() {
  const token = getAuthToken()

  if (token) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />

        <Route element={<GuestRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<ProtectedLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/review-jurnal" element={<ReviewJurnalPage />} />
            <Route path="/analisis/:analysisId" element={<AnalisisJurnalPage />} />
            <Route path="/history-jurnal" element={<HistoryJurnalPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
