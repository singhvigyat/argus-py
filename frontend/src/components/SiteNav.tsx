import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import AuthMenu from './AuthMenu';
import { useAuth } from '../auth/AuthContext';

type Props = {
  right?: ReactNode;
};

export default function SiteNav({ right }: Props) {
  const { user } = useAuth();

  return (
    <header className="site-nav">
      <Link to="/" className="wordmark">
        argus
      </Link>
      <span className="nav-meta">multi-agent ux</span>
      <div className="nav-right">
        {user ? (
          <Link to="/history" className="nav-back">
            History
          </Link>
        ) : null}
        {right}
        <AuthMenu />
      </div>
    </header>
  );
}
