const TOKEN_KEY = 'chess-intuition-access-token';

export function getAccessToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function saveAccessToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}
