import { useState, type CSSProperties, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { startAnalysis } from '../services/api';
import { PERSONAS } from '../data/personas';
import SiteNav from '../components/SiteNav';
import Rise from '../components/Rise';
import Reveal from '../components/Reveal';
import HeroTape from '../components/HeroTape';
import { useAuth } from '../auth/AuthContext';

const EXAMPLE_URLS = [
  'https://stripe.com',
  'https://linear.app',
  'https://notion.so',
  'https://vercel.com',
];

const FEATURES = [
  {
    index: '01',
    title: 'Independent reads',
    desc: 'Each persona is a separate pass. They do not share notes until the end.',
  },
  {
    index: '02',
    title: 'Three viewports',
    desc: 'Desktop, tablet, and mobile, captured as each reader would actually see them.',
  },
  {
    index: '03',
    title: 'Disagreement as signal',
    desc: 'Where readers conflict, the interface is making a trade-off. We name it.',
  },
  {
    index: '04',
    title: 'Contrast and type',
    desc: 'Low-vision and late-life readers check size, contrast, and tap targets.',
  },
  {
    index: '05',
    title: 'Weighted severity',
    desc: 'Findings are ranked across personas, not averaged into a hollow score.',
  },
  {
    index: '06',
    title: 'Concrete fixes',
    desc: 'Every issue comes with an observation, an impact, and a specific change.',
  },
];

export default function HomePage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>(['elderly_non_technical']);
  const navigate = useNavigate();
  const { user, quota, dailyLimit, setQuota } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    if (!user) {
      setError('Sign in with Google to run a reading.');
      return;
    }
    if (selectedPersonas.length === 0) {
      setError('Select at least one reader.');
      return;
    }
    if (quota && quota.remaining <= 0) {
      setError(`Daily limit reached (${dailyLimit} readings). Come back tomorrow.`);
      return;
    }

    setError('');
    setLoading(true);

    try {
      const { jobId, quota: nextQuota } = await startAnalysis(url.trim(), selectedPersonas);
      if (nextQuota) setQuota(nextQuota);
      navigate(`/report/${jobId}`);
    } catch (err) {
      setError((err as Error).message || 'Could not start. Is the backend running?');
      setLoading(false);
    }
  };

  const togglePersona = (id: string) => {
    setSelectedPersonas((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  return (
    <div className="page">
      <SiteNav />

      <section className="hero">
        <h1 className="hero-title">
          <Rise delay={0}>Four people,</Rise>
          <Rise delay={90}>one interface,</Rise>
          <Rise delay={180}>
            <em>then they disagree.</em>
          </Rise>
        </h1>

        <div className="hero-aside fade-rise" style={{ '--d': '420ms' } as CSSProperties}>
          <p className="hero-dek">
            Submit a URL. Four independent readers look at the same screen the way real people
            would: elderly, impatient, arriving cold, seeing poorly. Then they argue about what
            fails.
          </p>

          <form onSubmit={handleSubmit} className="url-form">
            <label className="kicker" htmlFor="website-url-input">
              Website
            </label>
            <div className="url-row" id="url-form-container">
              <input
                id="website-url-input"
                type="text"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setError('');
                }}
                placeholder="https://stripe.com"
                disabled={loading}
                autoComplete="url"
                spellCheck={false}
              />
              <button
                id="start-analysis-btn"
                type="submit"
                disabled={loading || !url.trim() || !user || (quota !== null && quota.remaining <= 0)}
                className="btn-primary"
              >
                {loading ? (
                  <>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      className="spin"
                    >
                      <path d="M21 12a9 9 0 11-6.219-8.56" />
                    </svg>
                    Starting
                  </>
                ) : (
                  <>
                    Analyze <span className="arrow">→</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {error && <p className="form-error">{error}</p>}

          {!user ? (
            <p className="auth-hint">
              Sign in with Google to run a reading. {dailyLimit} per account per day.
            </p>
          ) : (
            <p className="auth-hint">
              {quota ? `${quota.remaining} of ${quota.limit} readings left today.` : `${dailyLimit} readings per day.`}
            </p>
          )}

          <div className="persona-picks">
            {PERSONAS.map((p) => {
              const isOn = selectedPersonas.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => togglePersona(p.id)}
                  className={`persona-pick ${isOn ? 'is-on' : ''}`}
                  aria-pressed={isOn}
                >
                  <span className="pick-box" aria-hidden />
                  <span className="pick-idx">{p.index}</span>
                  <span>
                    <span className="pick-name">{p.name}</span>
                    <span className="pick-role">
                      {p.age} · {p.role}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>

          <div className="try-row">
            <span className="kicker">Try</span>
            {EXAMPLE_URLS.map((exUrl) => (
              <button key={exUrl} type="button" className="try-chip" onClick={() => setUrl(exUrl)}>
                {new URL(exUrl).hostname}
              </button>
            ))}
          </div>
        </div>
      </section>

      <HeroTape />

      <section className="section-block is-follow">
        <div className="section-head">
          <span className="kicker">Notes</span>
          <h2>What gets read</h2>
        </div>
        <div className="feature-grid">
          {FEATURES.map((feature, i) => (
            <Reveal key={feature.title} className="feature" delay={i * 50}>
              <div className="feature-idx">{feature.index}</div>
              <h3>{feature.title}</h3>
              <p>{feature.desc}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <footer className="site-foot">
        <span>Four readers. One screen.</span>
        <span>·</span>
        <span>Vision by Gemini</span>
        <span>·</span>
        <span>Capture by Playwright</span>
      </footer>
    </div>
  );
}
