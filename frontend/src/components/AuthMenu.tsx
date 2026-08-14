import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../auth/AuthContext';

export default function AuthMenu() {
  const { ready, configured, user, quota, login, logout } = useAuth();
  const [error, setError] = useState('');

  if (!ready) {
    return <span className="auth-status">…</span>;
  }

  if (!user) {
    if (!configured) {
      return <span className="auth-status">Sign-in unavailable</span>;
    }

    return (
      <div className="auth-menu">
        <GoogleLogin
          onSuccess={(response) => {
            if (response.credential) {
              setError('');
              void login(response.credential).catch((err: unknown) => {
                setError((err as Error).message || 'Sign-in failed');
              });
            }
          }}
          onError={() => {
            setError('Google sign-in was cancelled.');
          }}
          theme="outline"
          size="medium"
          text="signin_with"
          shape="pill"
        />
        {error ? <span className="auth-status">{error}</span> : null}
      </div>
    );
  }

  const remaining = quota?.remaining ?? 0;
  const limit = quota?.limit;
  const quotaLabel = limit != null ? `${remaining} of ${limit} left` : `${remaining} left today`;
  const initials = user.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  return (
    <div className="auth-menu is-signed-in">
      <div className="auth-chip">
        <span className="auth-avatar" aria-hidden="true">
          <span className="auth-initials">{initials || '?'}</span>
          {user.picture ? (
            <img
              src={user.picture}
              alt=""
              referrerPolicy="no-referrer"
              onError={(event) => {
                event.currentTarget.style.display = 'none';
              }}
            />
          ) : null}
        </span>
        <span className="auth-meta">
          <span className="auth-name">{user.name}</span>
          <span className="auth-quota">{quotaLabel}</span>
        </span>
        <span className="auth-divider" aria-hidden="true" />
        <button type="button" className="auth-signout" onClick={() => void logout()}>
          Sign out
        </button>
      </div>
    </div>
  );
}
