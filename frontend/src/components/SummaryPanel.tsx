import type { UXReport } from '../types';
import { useCountUp } from '../hooks/useCountUp';

interface Props {
  report: UXReport;
}

function scoreTone(score: number) {
  if (score <= 3) return 'is-ok';
  if (score <= 6) return 'is-mid';
  return 'is-bad';
}

function scoreLabel(score: number) {
  if (score <= 3) return 'Holds together';
  if (score <= 6) return 'Needs work';
  return 'Critical';
}

function OverallScore({ score }: { score: number }) {
  const n = useCountUp(score, 1400);
  return (
    <div className="score-hero">
      <div className={`num ${scoreTone(score)}`}>{n.toFixed(1)}</div>
      <div className="lbl">Severity / 10</div>
      <div className="tag">{scoreLabel(score)}</div>
    </div>
  );
}

export default function SummaryPanel({ report }: Props) {
  return (
    <div>
      <div className="report-mast">
        <OverallScore score={report.severityScore} />
        <div>
          <p className="report-copy">{report.summary}</p>
          <div className="stat-row">
            {[
              { label: 'Readers', value: report.personaInsights.length },
              { label: 'Issues', value: report.majorIssues.length },
              { label: 'Conflicts', value: report.conflicts.length },
              { label: 'Fixes', value: report.recommendations.length },
            ].map((stat) => (
              <div key={stat.label} className="stat">
                <div className="n">{stat.value}</div>
                <div className="l">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {(report.majorIssues.length > 0 || report.recommendations.length > 0) && (
        <div className="report-lists">
          {report.majorIssues.length > 0 && (
            <div className="report-list">
              <h3>Major issues</h3>
              <ol>
                {report.majorIssues.slice(0, 4).map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ol>
            </div>
          )}
          {report.recommendations.length > 0 && (
            <div className="report-list">
              <h3>Recommendations</h3>
              <ol>
                {report.recommendations.slice(0, 3).map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
