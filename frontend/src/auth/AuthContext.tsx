import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import {
  fetchAuthConfig,
  fetchMe,
  loginWithGoogle,
  logout as apiLogout,
  type AuthConfig,
  type AuthUser,
  type QuotaSnapshot,
} from '../services/api';

type AuthContextValue = {
  ready: boolean;
  configured: boolean;
  user: AuthUser | null;
  quota: QuotaSnapshot | null;
  dailyLimit: number;
  login: (credential: string) => Promise<void>;
  logout: () => Promise<void>;
  setQuota: (quota: QuotaSnapshot) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function AuthStateProvider({
  children,
  config,
  configReady,
}: {
  children: ReactNode;
  config: AuthConfig | null;
  configReady: boolean;
}) {
  const [sessionReady, setSessionReady] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [quota, setQuota] = useState<QuotaSnapshot | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchMe()
      .then((session) => {
        if (cancelled) return;
        if (session) {
          setUser(session.user);
          setQuota(session.quota);
        }
      })
      .catch((error: unknown) => {
        console.warn('[Auth] Could not load session', error);
      })
      .finally(() => {
        if (!cancelled) setSessionReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (credential: string) => {
    const session = await loginWithGoogle(credential);
    setUser(session.user);
    setQuota(session.quota);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setQuota(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready: configReady && sessionReady,
      configured: Boolean(config?.configured && config.googleClientId),
      user,
      quota,
      dailyLimit: config?.dailyLimit ?? 3,
      login,
      logout,
      setQuota,
    }),
    [config, configReady, sessionReady, user, quota, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [configReady, setConfigReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    fetchAuthConfig()
      .then((next) => {
        if (!cancelled) setConfig(next);
      })
      .catch(() => {
        if (!cancelled) setConfig(null);
      })
      .finally(() => {
        if (!cancelled) setConfigReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const inner = (
    <AuthStateProvider config={config} configReady={configReady}>
      {children}
    </AuthStateProvider>
  );

  if (config?.googleClientId) {
    return <GoogleOAuthProvider clientId={config.googleClientId}>{inner}</GoogleOAuthProvider>;
  }

  return inner;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
