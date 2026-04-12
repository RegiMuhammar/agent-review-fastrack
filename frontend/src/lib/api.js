const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

async function apiRequest(path, options = {}) {
  const { method = 'GET', body, token } = options

  const headers = {
    Accept: 'application/json',
  }

  if (body) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      payload?.message ||
      payload?.errors?.email?.[0] ||
      'Terjadi kesalahan saat menghubungi server.'
    throw new Error(message)
  }

  return payload
}

export function register(body) {
  return apiRequest('/v1/auth/register', { method: 'POST', body })
}

export function login(body) {
  return apiRequest('/v1/auth/login', { method: 'POST', body })
}

export function logout(token) {
  return apiRequest('/v1/auth/logout', { method: 'POST', token })
}

export function getMe(token) {
  return apiRequest('/v1/auth/me', { method: 'GET', token })
}
