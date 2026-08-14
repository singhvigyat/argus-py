import { useEffect, useState } from 'react';
import type { ScreenshotSet } from '../types';
import { assetUrl } from '../services/api';

interface Props {
  screenshots: ScreenshotSet;
  url: string;
}

type Tab = 'desktop' | 'mobile' | 'tablet';

const TABS: { id: Tab; label: string }[] = [
  { id: 'desktop', label: 'Desktop' },
  { id: 'mobile', label: 'Mobile' },
  { id: 'tablet', label: 'Tablet' },
];

export default function ScreenshotViewer({ screenshots, url }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('desktop');
  const [lightbox, setLightbox] = useState(false);
  const [showLabels, setShowLabels] = useState(true);

  const getSrc = () => {
    let src = screenshots[activeTab];
    if (showLabels) {
      if (activeTab === 'desktop') src = src.replace('desktop.png', 'som-desktop.png');
      if (activeTab === 'mobile') src = src.replace('mobile.png', 'som-mobile.png');
      if (activeTab === 'tablet') src = src.replace('tablet.png', 'som-tablet.png');
    }
    return assetUrl(src);
  };

  const currentSrc = getSrc();

  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setLightbox(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightbox]);

  return (
    <div className="shot-frame">
      <div className="shot-bar">
        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              id={`screenshot-tab-${tab.id}`}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="shot-actions">
          <button
            type="button"
            className={`quiet-btn ${showLabels ? 'is-on' : ''}`}
            onClick={() => setShowLabels(!showLabels)}
          >
            {showLabels ? 'Labels on' : 'Labels off'}
          </button>
          <a href={currentSrc} target="_blank" rel="noreferrer" className="quiet-btn">
            Open full ↗
          </a>
        </div>
      </div>

      <div
        className={`shot-stage ${activeTab === 'mobile' ? 'is-mobile' : ''} ${activeTab === 'tablet' ? 'is-tablet' : ''}`}
        onClick={() => setLightbox(true)}
      >
        <img src={currentSrc} alt={`${activeTab} screenshot of ${url}`} loading="lazy" />
        <span className="shot-hint">Click to enlarge</span>
      </div>

      {lightbox && (
        <div className="lightbox" onClick={() => setLightbox(false)} role="presentation">
          <img src={currentSrc} alt="Enlarged screenshot" />
        </div>
      )}
    </div>
  );
}
