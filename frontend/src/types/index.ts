/**
 * Re-exports all types for convenient import within the backend.
 * These types are also mirrored in shared/types/index.ts for the frontend.
 */

export type Viewport = 'desktop' | 'tablet' | 'mobile';

export type Persona = {
  id: string;
  name: string;
  age: number;
  background: string;
  goals: string[];
  painPoints: string[];
  traits: {
    readingSpeed: 'slow' | 'fast' | 'medium';
    visionAcuity: 'reduced' | 'normal' | 'high';
    techFamiliarity: 'low' | 'medium' | 'high';
    attentionSpan: 'short' | 'medium' | 'long';
    errorTolerance: 'low' | 'medium' | 'high';
  };
  heuristics: string[];
};

export type UXIssue = {
  elementId: number;           // must match an ID in the UI Structure JSON
  elementDescription: string;  // brief description of what the element is
  section: string;             // section the element belongs to
  heuristic: string;           // which heuristic this violates
  observation: string;         // what the persona noticed (1-2 sentences, first person)
  impact: string;              // why this matters for this persona specifically
  severity: "low" | "medium" | "high" | "critical";
  recommendation: string;      // one concrete fix
  verification?: IssueVerification;
};

export type IssueVerification = {
  verdict: 'verified' | 'unverified';
  evidence: string;
  note: string;
};

export type PersonaAnalysis = {
  personaId: string;
  personaName: string;
  viewport: Viewport;
  reasoning: string;           // 2-4 sentences of thinking before issues list (chain-of-thought)
  issues: UXIssue[];
  positives: string[];         // 1-3 things this persona found easy or good
  overallScore: number;        // 1-10, this persona's experience rating
};

export type ConflictType = 'severity_disagreement' | 'persona_opposition' | 'semantic_conflict';

export type Conflict = {
  elementId: number | null;
  elementDescription: string;
  section: string;
  conflictType: ConflictType;
  personasInvolved: string[];
  summary: string;
  designImplication: string;
};

export type ConflictReport = {
  totalConflicts: number;
  conflicts: Conflict[];
  mostContestedElement: number | null;
};

export interface ScreenshotSet {
  desktop: string;
  mobile: string;
  tablet: string;
}

export type JobStatus = 'pending' | 'processing' | 'complete' | 'error';

export interface UXReport {
  jobId: string;
  url: string;
  status: JobStatus;
  screenshots: ScreenshotSet;
  selectedPersonas: string[];
  personaInsights: PersonaAnalysis[];
  conflicts: Conflict[];
  conflictReport: ConflictReport;
  summary: string;
  majorIssues: string[];
  recommendations: string[];
  verificationResults: VerificationResult[];
  verificationSummary: VerificationSummary;
  severityScore: number;
  analysisTime: number;
  error?: string;
  createdAt: string;
  completedAt?: string;
}

export interface AnalyzeRequest {
  url: string;
}

export interface AnalyzeResponse {
  jobId: string;
  message: string;
}

export interface UIStructure {
  viewport: string;
  pageWidth?: number;
  elementCount?: number;
  elements: UIElement[];
  sections: Record<string, number[]>;
}

export type UIElement = {
  id: number;
  tag: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fontSize: number;
  color: string;
  backgroundColor: string;
  role: string;
  ariaLabel: string;
  isClickable: boolean;
  section: string;
  imageOnly: boolean;
};

export type VerificationVerdict = 'verified' | 'unverified' | 'element_not_found';

export type VerificationResult = {
  issueElementId: number;
  personaId: string;
  verdict: VerificationVerdict;
  evidence: string;
  note: string;
};

export type VerificationSummary = {
  verified: number;
  unverified: number;
  elementNotFound: number;
  removedIssueCount: number;
  totalIssueCount: number;
  removedIssueRatio: number;
};
