import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import SiteNav from '../components/SiteNav';
import { useAuth } from '../auth/AuthContext';
import { assetUrl, listReports, type ReportListItem } from '../services/api';
import { hostnameOf } from '../data/personas';
import type { JobStatus } from '../types';

const PAGE_SIZE = 20;

function statusLabel(status: JobStatus): string {
  if (status === 'complete') return 'Complete';
  if (status === 'processing') return 'Reading';
  if (status === 'pending') return 'Queued';
  return 'Failed';
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default function HistoryPage() {
  const { ready, user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<ReportListItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [hasMore, setHasMore] = useState(false);

  const load = useCallback(
    async (nextOffset: number, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError('');
      try {
        const page = await listReports({ limit: PAGE_SIZE, offset: nextOffset });
        setItems((prev) => (append ? [...prev, ...page] : page));
        setOffset(nextOffset);
        setHasMore(page.length === PAGE_SIZE);
      } catch (err) {
        setError((err as Error).message || 'Could not load history.');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!ready || !user) return;
    void load(0, false);
  }, [ready, user, load]);

  if (!ready) {
    return (
      <div className="page">
        <SiteNav />
        <p className="auth-hint">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="page">
        <SiteNav />
        <div className="history-empty">
          <h1>Your readings</h1>
          <p>Sign in with Google to see past reports.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <SiteNav />
      <section className="history-page">
        <div className="section-head">
          <span className="kicker">Archive</span>
          <h1>Your readings</h1>
        </div>

        {error ? <p className="form-error">{error}</p> : null}

        {loading ? <p className="auth-hint">Loading readings…</p> : null}

        {!loading && !error && items.length === 0 ? (
          <div className="history-empty">
            <p className="empty-note">No readings yet.</p>
            <button type="button" className="btn-primary" onClick={() => navigate('/')}>
              Start a reading <span className="arrow">→</span>
            </button>
          </div>
        ) : null}

        <ul className="history-list">
          {items.map((item) => (
            <li key={item.jobId}>
              <Link to={`/report/${item.jobId}`} className="history-row">
                <span className="history-thumb" aria-hidden="true">
                  {item.screenshot ? (
                    <img src={assetUrl(item.screenshot)} alt="" />
                  ) : (
                    <span className="history-thumb-empty" />
                  )}
                </span>
                <span className="history-body">
                  <span className="history-host">{hostnameOf(item.url)}</span>
                  <span className="history-meta">
                    <span className={`history-status is-${item.status}`}>{statusLabel(item.status)}</span>
                    <span>{formatWhen(item.createdAt)}</span>
                    {item.status === 'complete' ? (
                      <span>Score {item.severityScore.toFixed(1)}</span>
                    ) : null}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>

        {hasMore ? (
          <button
            type="button"
            className="nav-back history-more"
            disabled={loadingMore}
            onClick={() => void load(offset + PAGE_SIZE, true)}
          >
            {loadingMore ? 'Loading…' : 'Load more'}
          </button>
        ) : null}
      </section>
    </div>
  );
}
