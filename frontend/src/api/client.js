// src/api/client.js
import { logger } from '../utils/logger';

export const API_BASE =
  (process.env.REACT_APP_API_BASE_URL?.replace(/\/+$/, '') || 'http://localhost:8000') + '/api';

export async function request(path, { method = 'GET', params = {}, body, timeout = 10000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  const url = new URL(`${API_BASE}${path}`);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  });

  const headers = { 'Content-Type': 'application/json' };

  try {
    logger.debug('api:request', { method, url: url.toString(), hasBody: !!body });

    const res = await fetch(url.toString(), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const isJson = (res.headers.get('content-type') || '').includes('application/json');
    const payload = isJson ? await res.json().catch(() => ({})) : await res.text();

    if (!res.ok) {
      const err = new Error(`HTTP ${res.status}`);
      err.status = res.status;
      err.payload = payload;
      logger.error('api:error', { url: url.toString(), status: res.status, payload });
      throw err;
    }

    logger.debug('api:response', { url: url.toString(), status: res.status });
    return payload;
  } catch (e) {
    if (e.name === 'AbortError') {
      const err = new Error(`Request timeout after ${timeout}ms`);
      err.code = 'ETIMEOUT';
      logger.warn('api:timeout', { url: url.toString(), timeout });
      throw err;
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export default request;