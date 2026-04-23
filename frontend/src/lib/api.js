const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim()

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
  const { method = 'GET', body, token, responseType = 'json' } = options

  if (!API_BASE_URL) {
    throw new Error('VITE_API_BASE_URL belum diset di frontend/.env')
  }

  const headers = {
    Accept: 'application/json',
  }

  const isFormData = body instanceof FormData

  if (body && !isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
  })

  if (responseType === 'blob') {
    if (!response.ok) {
      throw new Error('Gagal mengambil file PDF.')
    }

    return response.blob()
  }

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

export function updateProfile(token, payload) {
  return request('/auth/profile', {
    method: 'PUT',
    token,
    body: payload,
  })
}

export function createAnalysis(token, payload) {
  const formData = new FormData()
  formData.append('doc_name', payload.docName)
  formData.append('doc_type', payload.docType)
  formData.append('file', payload.file)

  return request('/auth/analyses', {
    method: 'POST',
    token,
    body: formData,
  })
}

export function listAnalyses(token) {
  return request('/auth/analyses', {
    method: 'GET',
    token,
  })
}

export function getAnalysis(token, analysisId) {
  return request(`/auth/analyses/${analysisId}`, {
    method: 'GET',
    token,
  })
}

export function deleteAnalysis(token, analysisId) {
  return request(`/auth/analyses/${analysisId}`, {
    method: 'DELETE',
    token,
  })
}

export function getAnalysisFileBlob(token, analysisId) {
  return request(`/auth/analyses/${analysisId}/file`, {
    method: 'GET',
    token,
    responseType: 'blob',
  })
}

export function submitAnalysisFeedback(token, analysisId, payload) {
  return request(`/auth/analysis/${analysisId}/feedback`, {
    method: 'POST',
    token,
    body: payload,
  })
}

export function listAnalysisFeedbacks(token, analysisId) {
  return request(`/auth/analysis/${analysisId}/feedback`, {
    method: 'GET',
    token,
  })
}

export function listPublicFeedbacks(options = {}) {
  const params = new URLSearchParams()

  if (options.page) {
    params.set('page', String(options.page))
  }

  if (options.limit) {
    params.set('limit', String(options.limit))
  }

  const queryString = params.toString()
  const path = queryString ? `/feedbacks?${queryString}` : '/feedbacks'

  return request(path, {
    method: 'GET',
  })
}

export function getAnalysisByAccessCode(payload) {
  return request('/analysis/access', {
    method: 'POST',
    body: payload,
  })
}
