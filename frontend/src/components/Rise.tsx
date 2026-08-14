import type { CSSProperties, ReactNode } from 'react';

type Props = {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: 'span' | 'div';
};

export default function Rise({ children, delay = 0, className = '', as: Tag = 'span' }: Props) {
  return (
    <Tag className={`rise ${className}`}>
      <span style={{ '--d': `${delay}ms` } as CSSProperties}>{children}</span>
    </Tag>
  );
}
