import type { UXReport } from '../types';

const API_ROOT = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '';
const API_BASE = `${API_ROOT}/api`;

export function assetUrl(path: string): string {
  if (!path || path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return `${API_ROOT}${path}`;
}

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  picture: string;
};

export type QuotaSnapshot = {
  used: number;
  limit: number;
  remaining: number;
  resetAt: string;
};

export type AuthConfig = {
  googleClientId: string;
  configured: boolean;
  dailyLimit: number;
  globalDailyLimit: number;
};

export type AuthResponse = {
  user: AuthUser;
  quota: QuotaSnapshot;
};

async function parseError(res: Response): Promise<string> {
  const err = await res.json().catch(() => ({ error: 'Unknown error' }));
  return err.error || `Server error: ${res.status}`;
}

function request(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  });
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const res = await request('/auth/config');
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function fetchMe(): Promise<AuthResponse | null> {
  const res = await request('/auth/me');
  if (res.status === 401) return null;
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function loginWithGoogle(credential: string): Promise<AuthResponse> {
  const res = await request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function logout(): Promise<void> {
  const res = await request('/auth/logout', { method: 'POST' });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
}

export async function startAnalysis(
  url: string,
  personaIds?: string[],
): Promise<{ jobId: string; message: string; quota?: QuotaSnapshot }> {
  const res = await request('/analyze', {
    method: 'POST',
    body: JSON.stringify({ url, personaIds }),
  });

  if (!res.ok) {
    throw new Error(await parseError(res));
  }

  return res.json();
}

export async function getAnalysisStatus(jobId: string): Promise<UXReport> {
  const res = await request(`/analyze/${jobId}`);

  if (!res.ok) {
    throw new Error(await parseError(res));
  }

  return res.json();
}
