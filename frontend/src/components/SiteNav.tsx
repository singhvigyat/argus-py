import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import AuthMenu from './AuthMenu';

type Props = {
  right?: ReactNode;
};

export default function SiteNav({ right }: Props) {
  return (
    <header className="site-nav">
      <Link to="/" className="wordmark">
        argus
      </Link>
      <span className="nav-meta">multi-agent ux</span>
      <div className="nav-right">
        {right}
        <AuthMenu />
      </div>
    </header>
  );
}
