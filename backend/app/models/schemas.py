from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Viewport = Literal["desktop", "tablet", "mobile"]
JobStatus = Literal["pending", "processing", "complete", "error"]
Severity = Literal["low", "medium", "high", "critical"]
ConflictType = Literal["severity_disagreement", "persona_opposition", "semantic_conflict"]
Verdict = Literal["verified", "unverified", "element_not_found"]
IssueVerdict = Literal["verified", "unverified"]


class DOMElement(BaseModel):
    id: int
    tag: str
    text: str
    x: int
    y: int
    width: int
    height: int
    fontSize: int = 0
    color: str = ""
    backgroundColor: str = ""
    role: str = ""
    ariaLabel: str = ""
    isClickable: bool = False
    section: str = ""
    imageOnly: bool = False


class UIStructure(BaseModel):
    viewport: Viewport
    pageWidth: int = 0
    elementCount: int = 0
    sections: dict[str, list[int]] = Field(default_factory=dict)
    elements: list[DOMElement] = Field(default_factory=list)


class PersonaTraits(BaseModel):
    readingSpeed: str
    visionAcuity: str
    techFamiliarity: str
    attentionSpan: str
    errorTolerance: str


class Persona(BaseModel):
    id: str
    name: str
    age: int
    background: str
    goals: list[str]
    painPoints: list[str]
    traits: PersonaTraits
    heuristics: list[str]


class IssueVerification(BaseModel):
    verdict: IssueVerdict
    evidence: str = ""
    note: str = ""


class UXIssue(BaseModel):
    elementId: int
    elementDescription: str
    section: str
    heuristic: str
    observation: str
    impact: str
    severity: Severity
    recommendation: str
    verification: IssueVerification | None = None


class PersonaAnalysis(BaseModel):
    personaId: str
    personaName: str
    viewport: Viewport
    reasoning: str
    issues: list[UXIssue] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)
    overallScore: float = Field(ge=1, le=10)


class Conflict(BaseModel):
    elementId: int | None
    elementDescription: str
    section: str
    conflictType: ConflictType
    personasInvolved: list[str]
    summary: str
    designImplication: str


class ConflictReport(BaseModel):
    totalConflicts: int = 0
    conflicts: list[Conflict] = Field(default_factory=list)
    mostContestedElement: int | None = None


class VerificationResult(BaseModel):
    issueElementId: int
    personaId: str
    verdict: Verdict
    evidence: str = ""
    note: str = ""


class VerificationSummary(BaseModel):
    verified: int = 0
    unverified: int = 0
    elementNotFound: int = 0
    removedIssueCount: int = 0
    totalIssueCount: int = 0
    removedIssueRatio: float = 0.0


class ScreenshotSet(BaseModel):
    desktop: str = ""
    tablet: str = ""
    mobile: str = ""


class Artifacts(BaseModel):
    screenshots: dict[str, str] = Field(default_factory=dict)
    domStructure: str = ""


class UXReport(BaseModel):
    jobId: str
    url: str
    status: JobStatus = "pending"
    screenshots: ScreenshotSet = Field(default_factory=ScreenshotSet)
    selectedPersonas: list[str] = Field(default_factory=list)
    personaInsights: list[PersonaAnalysis] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    conflictReport: ConflictReport = Field(default_factory=ConflictReport)
    summary: str = ""
    majorIssues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    verificationResults: list[VerificationResult] = Field(default_factory=list)
    verificationSummary: VerificationSummary = Field(default_factory=VerificationSummary)
    severityScore: float = 0.0
    analysisTime: int = 0
    error: str | None = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    completedAt: datetime | None = None
    artifacts: Artifacts = Field(default_factory=Artifacts)
    viewport: Viewport = "desktop"
    ownerId: str | None = None


class ReportListItem(BaseModel):
    jobId: str
    url: str
    status: JobStatus
    severityScore: float = 0.0
    createdAt: datetime
    completedAt: datetime | None = None
    screenshot: str = ""


class AnalyzeRequest(BaseModel):
    url: str
    personaIds: list[str] | None = None
    viewport: Viewport = "desktop"


class QuotaSnapshot(BaseModel):
    used: int
    limit: int
    remaining: int
    resetAt: str


class AnalyzeResponse(BaseModel):
    jobId: str
    message: str = "Analysis started. Poll GET /api/analyze/{jobId} for results."
    quota: QuotaSnapshot | None = None


class AuthUser(BaseModel):
    id: str
    email: str
    name: str
    picture: str = ""


class AuthConfig(BaseModel):
    googleClientId: str
    configured: bool
    dailyLimit: int
    globalDailyLimit: int


class AuthResponse(BaseModel):
    user: AuthUser
    quota: QuotaSnapshot


class GoogleLoginRequest(BaseModel):
    credential: str
