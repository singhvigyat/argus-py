import { useMemo } from 'react';
import type { UXReport } from '../types';
import { getPersonaMeta, hostnameOf } from '../data/personas';

interface Props {
  report: UXReport | null;
}

function pad(n: number) {
  return String(n).padStart(2, '0');
}

export default function AnalysisProgress({ report }: Props) {
  const completedPersonas = report?.personaInsights.map((p) => p.personaId) ?? [];
  const hasScreenshots = !!report?.screenshots?.desktop;
  const selectedPersonas = report?.selectedPersonas ?? ['elderly_non_technical'];

  const steps = useMemo(() => {
    const list: { id: string; label: string }[] = [
      { id: 'screenshot', label: 'Capturing screens' },
    ];

    selectedPersonas.forEach((pid) => {
      const meta = getPersonaMeta(pid);
      list.push({ id: pid, label: `Reading as ${meta.name}` });
    });

    list.push({ id: 'aggregate', label: 'Cross-examining notes' });
    return list;
  }, [selectedPersonas]);

  const getStepStatus = (stepId: string): 'done' | 'active' | 'pending' => {
    if (stepId === 'screenshot') {
      return hasScreenshots ? 'done' : report?.status === 'processing' ? 'active' : 'pending';
    }
    if (stepId === 'aggregate') {
      return report?.status === 'processing' && completedPersonas.length === selectedPersonas.length
        ? 'active'
        : 'pending';
    }
    if (completedPersonas.includes(stepId)) return 'done';
    if (hasScreenshots && report?.status === 'processing') {
      if (selectedPersonas.includes(stepId) && !completedPersonas.includes(stepId)) return 'active';
    }
    return 'pending';
  };

  const doneCount = steps.filter((s) => getStepStatus(s.id) === 'done').length;
  const progress = Math.max(6, (doneCount / steps.length) * 100);
  const host = report?.url ? hostnameOf(report.url) : null;

  return (
    <>
      <div className="progress-rail" aria-hidden>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="progress-page fade-rise">
        <div className="progress-kicker kicker">In progress</div>
        <h2 className="progress-title">Reading</h2>
        {host ? <p className="progress-host">{host}</p> : null}
        <p className="progress-note">
          {host
            ? 'Independent passes, then a comparison. Usually a minute.'
            : 'Opening the pipeline.'}
        </p>

        <div className="reading-bar" aria-hidden>
          <i />
        </div>

        <div className="step-list">
          {steps.map((step, idx) => {
            const status = getStepStatus(step.id);
            const cls = status === 'done' ? 'is-done' : status === 'active' ? 'is-on' : '';
            const stateLabel = status === 'done' ? 'done' : status === 'active' ? 'now' : 'wait';

            return (
              <div key={step.id} className={`step ${cls}`}>
                <span className="step-idx">{pad(idx + 1)}</span>
                <span className="step-label">{step.label}</span>
                <span className="step-state">{stateLabel}</span>
              </div>
            );
          })}
        </div>

        {completedPersonas.length > 0 && (
          <p className="progress-count">
            {completedPersonas
              .map((pid) => getPersonaMeta(pid).name)
              .join(' · ')}
            {' · '}
            {completedPersonas.length}/{selectedPersonas.length} readers
          </p>
        )}
      </div>
    </>
  );
}
