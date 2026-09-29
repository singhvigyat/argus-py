export type PersonaMeta = {
  id: string;
  name: string;
  age: number;
  role: string;
  lens: string;
  initial: string;
  index: string;
};

export const PERSONAS: PersonaMeta[] = [
  {
    id: 'elderly_non_technical',
    name: 'Maya',
    age: 62,
    role: 'Retired teacher',
    lens: 'Reads slowly. Needs large type, plain labels, few steps.',
    initial: 'M',
    index: '01',
  },
  {
    id: 'developer',
    name: 'Dev',
    age: 24,
    role: 'Engineer',
    lens: 'Wants the shortest path. Intolerant of ceremony.',
    initial: 'D',
    index: '02',
  },
  {
    id: 'first_time_visitor',
    name: 'Arjun',
    age: 28,
    role: 'First visit',
    lens: 'Ten seconds to understand the offer, or he leaves.',
    initial: 'A',
    index: '03',
  },
  {
    id: 'visually_impaired',
    name: 'Priya',
    age: 34,
    role: 'Low vision',
    lens: 'Zooms to 150%. Needs contrast, size, and obvious targets.',
    initial: 'P',
    index: '04',
  },
];

export function getPersonaMeta(id: string, fallbackName?: string): PersonaMeta {
  const found = PERSONAS.find((p) => p.id === id);
  if (found) return found;
  const name = fallbackName || id;
  return {
    id,
    name,
    age: 0,
    role: '',
    lens: '',
    initial: name.charAt(0).toUpperCase() || '·',
    index: '00',
  };
}

export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url || '?';
  }
}
