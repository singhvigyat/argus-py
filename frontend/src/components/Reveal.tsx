import { useRef, type CSSProperties, type ReactNode } from 'react';
import { useInView } from '../hooks/useInView';

type Props = {
  children: ReactNode;
  className?: string;
  delay?: number;
  style?: CSSProperties;
};

export default function Reveal({ children, className = '', delay = 0, style }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);

  return (
    <div
      ref={ref}
      className={`reveal ${inView ? 'is-in' : ''} ${className}`}
      style={{ '--d': `${delay}ms`, ...style } as CSSProperties}
    >
      {children}
    </div>
  );
}
