const BASE = (import.meta.env.VITE_EDGE_BASE || 'https://dhkalign-edge-production.tnfy4np8pm.workers.dev').replace(/\/+$/, '')

let _memKey = ''
export function getApiKey() {
  if (_memKey) return _memKey
  try {
    _memKey = sessionStorage.getItem('dhk_api_key') || ''
    if (!_memKey) {
      _memKey = localStorage.getItem('dhk_api_key') || ''
    }
  } catch (_) {}
  return _memKey
}

export async function api(path, opts = {}) {
  const url = `${BASE}${path.startsWith('/') ? path : '/'+path}`
  const key = getApiKey()
  const headers = new Headers(opts.headers || {})
  headers.set('accept', 'application/json')
  if (opts.body && !(opts.body instanceof FormData)) headers.set('content-type', 'application/json')
  if (key) headers.set('x-api-key', key)

  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers,
    body: opts.body
      ? (opts.body instanceof FormData ? opts.body : JSON.stringify(opts.body))
      : undefined
  })

  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch (_) {}

  if (!res.ok) {
    // normalize errors; never throw HTML
    throw (data && typeof data === 'object') ? data : { ok: false, error: 'bad_status', status: res.status, raw: text }
  }
  return data
}

export const get  = (p, h={})          => api(p, { method:'GET',  headers:h })
export const post = (p, body, h={})     => api(p, { method:'POST', body, headers:h })

export const request = api
