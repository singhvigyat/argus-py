import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAnalysisStatus } from '../services/api';
import type { UXReport } from '../types';
import AnalysisProgress from '../components/AnalysisProgress';
import ScreenshotViewer from '../components/ScreenshotViewer';
import PersonaCard from '../components/PersonaCard';
import ConflictSection from '../components/ConflictSection';
import SummaryPanel from '../components/SummaryPanel';
import SiteNav from '../components/SiteNav';
import { hostnameOf } from '../data/personas';

const POLL_INTERVAL = 2500;

export default function ReportPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<UXReport | null>(null);
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const data = await getAnalysisStatus(jobId);
        setReport(data);

        if (data.status === 'complete' || data.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (err) {
        setError((err as Error).message);
        if (pollRef.current) clearInterval(pollRef.current);
      }
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]);

  const isLoading = !report || report.status === 'pending' || report.status === 'processing';

  if (error) {
    return (
      <div className="page">
        <SiteNav />
        <div className="error-page">
          <h2>Something slipped.</h2>
          <p>{error}</p>
          <button type="button" className="btn-primary" onClick={() => navigate('/')}>
            ← Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <SiteNav
        right={
          <button
            type="button"
            id="back-to-home-btn"
            className="nav-back"
            onClick={() => navigate('/')}
          >
            ← New reading
          </button>
        }
      />

      {isLoading && <AnalysisProgress report={report} />}

      {report?.status === 'error' && (
        <div className="fail-banner">
          <h3>The reading failed</h3>
          <p>{report.error || 'An unknown error occurred during analysis.'}</p>
        </div>
      )}

      {report?.status === 'complete' && (
        <div className="fade-rise">
          <div className="report-host">
            <h1>{hostnameOf(report.url)}</h1>
            <span className="meta mono">{report.url}</span>
          </div>

          <SummaryPanel report={report} />

          <section className="section-block">
            <div className="section-head">
              <span className="kicker">01</span>
              <h2>Captured screens</h2>
            </div>
            <ScreenshotViewer screenshots={report.screenshots} url={report.url} />
          </section>

          <section className="section-block">
            <div className="section-head">
              <span className="kicker">02</span>
              <h2>Four readings</h2>
              {report.analysisTime ? (
                <span className="section-meta">
                  {(report.analysisTime / 1000).toFixed(1)}s
                </span>
              ) : null}
            </div>
            <div className="reading-grid">
              {report.personaInsights.map((insight, i) => (
                <PersonaCard key={insight.personaId} insight={insight} index={i} />
              ))}
            </div>
          </section>

          {report.conflicts.length > 0 && (
            <section className="section-block">
              <div className="section-head">
                <span className="kicker">03</span>
                <h2>Where they disagree</h2>
              </div>
              <ConflictSection conflicts={report.conflicts} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}
