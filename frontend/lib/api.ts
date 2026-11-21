import { getAccessToken } from './auth';

export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
