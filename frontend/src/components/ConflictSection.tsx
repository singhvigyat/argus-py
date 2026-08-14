import type { Conflict } from '../types';
import { getPersonaMeta } from '../data/personas';
import Reveal from './Reveal';

interface Props {
  conflicts: Conflict[];
}

const conflictTypeLabel: Record<Conflict['conflictType'], string> = {
  severity_disagreement: 'Severity',
  persona_opposition: 'Opposition',
  semantic_conflict: 'Semantic',
};

export default function ConflictSection({ conflicts }: Props) {
  if (conflicts.length === 0) {
    return <p className="empty-note">No disagreements. The readers aligned.</p>;
  }

  return (
    <div className="conflict-list">
      {conflicts.map((conflict, idx) => (
        <Reveal key={`${conflict.conflictType}-${conflict.elementId ?? 'general'}-${idx}`} delay={idx * 60}>
          <article className="conflict">
            <div className="conflict-top">
              <strong>{conflict.elementDescription}</strong>
              <span className="conflict-type">{conflictTypeLabel[conflict.conflictType]}</span>
            </div>
            <div className="conflict-body">
              <div className="conflict-meta">
                <span>{conflict.section || 'General'}</span>
                <span className="mono">#{conflict.elementId ?? '?'}</span>
                <span>
                  {conflict.personasInvolved
                    .map((id) => getPersonaMeta(id).name)
                    .join(' · ')}
                </span>
              </div>
              <p>{conflict.summary}</p>
              <p className="implication">{conflict.designImplication}</p>
            </div>
          </article>
        </Reveal>
      ))}
    </div>
  );
}
