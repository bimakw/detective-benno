"""Data models for Detective Benno."""

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for investigation findings."""

    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


class ReviewComment(BaseModel):
    """A single finding from code investigation."""

    file_path: str = Field(..., description="Path to the file being investigated")
    line_start: int = Field(..., description="Starting line number")
    line_end: int | None = Field(None, description="Ending line number")
    severity: Severity = Field(..., description="Severity level of the finding")
    category: str = Field(..., description="Category (security, performance, etc.)")
    message: str = Field(..., description="Description of the finding")
    suggestion: str | None = Field(None, description="Suggested fix or improvement")
    code_snippet: str | None = Field(None, description="Relevant code snippet")
    suggested_code: str | None = Field(None, description="Suggested replacement code")

    @property
    def line_range(self) -> str:
        """Get line range as string."""
        if self.line_end and self.line_end != self.line_start:
            return f"{self.line_start}-{self.line_end}"
        return str(self.line_start)


class ReviewResult(BaseModel):
    """Result of a code investigation."""

    files_reviewed: int = Field(default=0, description="Number of files investigated")
    comments: list[ReviewComment] = Field(default_factory=list)
    summary: str | None = Field(None, description="Overall investigation summary")
    model_used: str = Field(default="gpt-4o", description="Model used for investigation")
    tokens_used: int = Field(default=0, description="Total tokens consumed")

    @property
    def critical_count(self) -> int:
        """Count of critical findings."""
        return sum(1 for c in self.comments if c.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for c in self.comments if c.severity == Severity.WARNING)

    @property
    def suggestion_count(self) -> int:
        """Count of suggestions."""
        return sum(1 for c in self.comments if c.severity == Severity.SUGGESTION)

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical findings."""
        return self.critical_count > 0


class FileChange(BaseModel):
    """Represents a changed file in a diff."""

    path: str = Field(..., description="File path")
    content: str | None = Field(None, description="Full file content")
    diff: str | None = Field(None, description="Diff content")
    language: str | None = Field(None, description="Programming language")
    added_lines: list[int] = Field(default_factory=list)
    removed_lines: list[int] = Field(default_factory=list)


class ReviewConfig(BaseModel):
    """Configuration for code investigation."""

    level: str = Field(default="standard", description="Investigation level")
    max_comments: int = Field(default=10, description="Max findings per investigation")
    guidelines: list[str] = Field(default_factory=list, description="Custom guidelines")
    ignore_files: list[str] = Field(default_factory=list, description="Files to ignore")
    ignore_patterns: list[str] = Field(default_factory=list, description="Patterns to ignore")
    model: str = Field(default="gpt-4o", description="Model to use")
    temperature: float = Field(default=0.3, description="Model temperature")
