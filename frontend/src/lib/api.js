const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function getErrorMessage(payload, fallbackMessage) {
  if (!payload) {
    return fallbackMessage
  }

  if (typeof payload.message === 'string' && payload.message.length > 0) {
    return payload.message
  }

  if (payload.errors && typeof payload.errors === 'object') {
    const firstFieldErrors = Object.values(payload.errors)[0]

    if (Array.isArray(firstFieldErrors) && firstFieldErrors[0]) {
      return String(firstFieldErrors[0])
    }
  }

  return fallbackMessage
}

async function request(path, options = {}) {
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

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(getErrorMessage(payload, 'Permintaan gagal diproses.'))
  }

  return payload
}

export function register(payload) {
  return request('/auth/register', {
    method: 'POST',
    body: payload,
  })
}

export function login(payload) {
  return request('/auth/login', {
    method: 'POST',
    body: payload,
  })
}

export function fetchMe(token) {
  return request('/auth/me', {
    method: 'GET',
    token,
  })
}

export function logout(token) {
  return request('/auth/logout', {
    method: 'POST',
    token,
  })
}
