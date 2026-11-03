import { supabase } from './supabase';

export const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const client = supabase();
  const { data } = client ? await client.auth.getSession() : { data: { session: null } };
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}), ...init.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
