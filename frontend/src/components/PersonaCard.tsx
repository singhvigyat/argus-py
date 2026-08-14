import { useState } from 'react';
import type { PersonaAnalysis, UXIssue } from '../types';
import { getPersonaMeta } from '../data/personas';
import Reveal from './Reveal';

interface Props {
  insight: PersonaAnalysis;
  index: number;
}

function severityClass(score: number): string {
  if (score <= 3) return 'sev-low';
  if (score <= 6) return 'sev-medium';
  return 'sev-high';
}

function severityLabel(score: number): string {
  if (score <= 3) return 'Low';
  if (score <= 6) return 'Medium';
  return 'High';
}

export default function PersonaCard({ insight, index }: Props) {
  const [expanded, setExpanded] = useState(true);
  const meta = getPersonaMeta(insight.personaId, insight.personaName);
  const issuesCount = insight.issues?.length || 0;

  return (
    <Reveal delay={index * 70}>
      <article className="reading-card" id={`persona-card-${insight.personaId}`}>
        <button
          type="button"
          className="reading-head"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
        >
          <div className="reading-id">
            <span className="initial">{meta.initial}</span>
            <div>
              <div className="reading-name">{insight.personaName}</div>
              <div className="reading-sub">
                {meta.index} · {issuesCount} issue{issuesCount !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
          <div className="reading-aside">
            <div className={`reading-score ${severityClass(insight.overallScore)}`}>
              {insight.overallScore}
            </div>
            <span className="reading-toggle" aria-hidden>
              {expanded ? '–' : '+'}
            </span>
          </div>
        </button>

        <div className={`reading-body ${expanded ? 'is-open' : ''}`}>
          <div className="inner">
            <div className="inner-pad">
              <span className={`sev ${severityClass(insight.overallScore)}`}>
                {severityLabel(insight.overallScore)} · {insight.overallScore}/10
              </span>

              {insight.reasoning && <blockquote className="quote">{insight.reasoning}</blockquote>}

              {insight.positives?.length > 0 && (
                <IssueSection title="What held up" items={insight.positives} />
              )}

              {insight.issues?.length > 0 && (
                <UXIssuesSection title="What failed" issues={insight.issues} />
              )}
            </div>
          </div>
        </div>
      </article>
    </Reveal>
  );
}

function IssueSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="issue-block">
      <h4>{title}</h4>
      <ul>
        {items.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function UXIssuesSection({ title, issues }: { title: string; issues: UXIssue[] }) {
  return (
    <div className="issue-block">
      <h4>{title}</h4>
      <ul>
        {issues.map((issue, idx) => {
          const isVerified = issue.verification?.verdict === 'verified';
          return (
            <li key={idx}>
              <div className="issue-obs">
                [{issue.elementId}] {issue.observation}
              </div>
              {isVerified && (
                <div className="verified">
                  Verified{issue.verification?.evidence ? ` · ${issue.verification.evidence}` : ''}
                </div>
              )}
              <div>
                <em>Impact.</em> {issue.impact}
              </div>
              <div className="issue-fix">Fix. {issue.recommendation}</div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
