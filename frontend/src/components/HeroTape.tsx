import type { CSSProperties } from 'react';

const TAPE = [
  { name: 'Maya', note: 'still on the headline' },
  { name: 'Dev', note: 'already wants the shortcut' },
  { name: 'Arjun', note: 'ten seconds, then gone' },
  { name: 'Priya', note: 'zoomed to one-fifty' },
  { name: 'Four readers', note: 'they do not share notes' },
  { name: 'One screen', note: 'then they disagree' },
];

function TapeSet({ hidden = false }: { hidden?: boolean }) {
  return (
    <ul className="hero-tape-set" aria-hidden={hidden || undefined}>
      {TAPE.map((item) => (
        <li key={item.name} className="hero-tape-item">
          <span className="tape-name">{item.name}</span>
          <i className="tape-dot" aria-hidden />
          <span className="tape-note">{item.note}</span>
        </li>
      ))}
    </ul>
  );
}

export default function HeroTape() {
  return (
    <div className="hero-tape fade-rise" style={{ '--d': '720ms' } as CSSProperties} aria-hidden>
      <div className="hero-tape-track">
        <TapeSet />
        <TapeSet hidden />
      </div>
    </div>
  );
}
