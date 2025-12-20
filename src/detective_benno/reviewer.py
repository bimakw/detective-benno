"""Core investigation engine for Detective Benno."""

from pathlib import Path

from detective_benno.models import (
    FileChange,
    ReviewComment,
    ReviewConfig,
    ReviewResult,
)
from detective_benno.prompts import build_review_prompt
from detective_benno.providers.base import LLMProvider
from detective_benno.providers.factory import ProviderFactory


class CodeReviewer:
    """AI-powered code investigator with multi-provider support.

    Supports multiple LLM providers including OpenAI and Ollama.
    """

    def __init__(
        self,
        config: ReviewConfig | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        """Initialize the code investigator.

        Args:
            config: Investigation configuration. Uses defaults if not provided.
            provider: LLM provider instance. If not provided, creates one from config.
        """
        self.config = config or ReviewConfig()
        self._provider = provider

    @property
    def provider(self) -> LLMProvider:
        """Get the LLM provider, creating one if needed."""
        if self._provider is None:
            provider_config = self.config.provider
            self._provider = ProviderFactory.create(
                provider_name=provider_config.name,
                api_key=provider_config.api_key,
                model=provider_config.model,
                base_url=provider_config.base_url,
            )
        return self._provider

    def review_files(self, files: list[FileChange]) -> ReviewResult:
        """Investigate multiple files and return aggregated results.

        Args:
            files: List of file changes to investigate.

        Returns:
            Aggregated investigation result.
        """
        all_comments: list[ReviewComment] = []
        total_tokens = 0
        files_reviewed = 0

        for file in files:
            if self._should_ignore_file(file.path):
                continue

            result = self._review_single_file(file)
            all_comments.extend(result.comments)
            total_tokens += result.tokens_used
            files_reviewed += 1

        return ReviewResult(
            files_reviewed=files_reviewed,
            comments=all_comments[: self.config.max_comments],
            model_used=self.config.provider.effective_model,
            tokens_used=total_tokens,
        )

    def review_diff(self, diff: str) -> ReviewResult:
        """Investigate a git diff string.

        Args:
            diff: Git diff content.

        Returns:
            Investigation result.
        """
        files = self._parse_diff(diff)
        return self.review_files(files)

    def review_file(self, path: str, content: str | None = None) -> ReviewResult:
        """Investigate a single file.

        Args:
            path: Path to the file.
            content: File content. If not provided, reads from disk.

        Returns:
            Investigation result.
        """
        if content is None:
            content = Path(path).read_text()

        file_change = FileChange(
            path=path,
            content=content,
            language=self._detect_language(path),
        )
        return self.review_files([file_change])

    def _review_single_file(self, file: FileChange) -> ReviewResult:
        """Investigate a single file change."""
        user_prompt = build_review_prompt(
            file=file,
            config=self.config,
        )
        system_prompt = self._get_system_prompt()

        comments, tokens_used = self.provider.review(
            file=file,
            config=self.config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return ReviewResult(
            files_reviewed=1,
            comments=comments,
            tokens_used=tokens_used,
            model_used=self.config.provider.effective_model,
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Detective Benno."""
        base_prompt = """You are Detective Benno, an expert code investigator. Your mission is to examine code changes and uncover issues before they become problems.

As a detective, you focus on:
1. Security vulnerabilities (SQL injection, XSS, hardcoded secrets, etc.)
2. Performance issues (N+1 queries, memory leaks, inefficient algorithms)
3. Best practices and code patterns
4. Error handling and edge cases
5. Maintainability and readability

Respond with a JSON object containing a "comments" array. Each finding should have:
- line_start: Starting line number
- line_end: Ending line number (optional)
- severity: "critical", "warning", "suggestion", or "info"
- category: "security", "performance", "best-practice", "error-handling", or "maintainability"
- message: Clear description of the finding
- suggestion: How to fix it (optional)
- suggested_code: Replacement code (optional)

Be thorough but fair. Only report real issues, not minor style preferences unless they significantly affect readability."""

        if self.config.guidelines:
            guidelines = "\n".join(f"- {g}" for g in self.config.guidelines)
            base_prompt += f"\n\nAdditional investigation guidelines:\n{guidelines}"

        return base_prompt

    def _should_ignore_file(self, path: str) -> bool:
        """Check if a file should be ignored."""
        from fnmatch import fnmatch

        for pattern in self.config.ignore_files:
            if fnmatch(path, pattern):
                return True
        return False

    def _parse_diff(self, diff: str) -> list[FileChange]:
        """Parse a git diff into FileChange objects."""
        files = []
        current_file = None
        current_diff_lines: list[str] = []

        for line in diff.split("\n"):
            if line.startswith("diff --git"):
                if current_file:
                    files.append(
                        FileChange(
                            path=current_file,
                            diff="\n".join(current_diff_lines),
                            language=self._detect_language(current_file),
                        )
                    )
                parts = line.split(" b/")
                current_file = parts[-1] if len(parts) > 1 else None
                current_diff_lines = [line]
            elif current_file:
                current_diff_lines.append(line)

        if current_file:
            files.append(
                FileChange(
                    path=current_file,
                    diff="\n".join(current_diff_lines),
                    language=self._detect_language(current_file),
                )
            )

        return files

    def _detect_language(self, path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
            ".swift": "swift",
            ".kt": "kotlin",
        }
        suffix = Path(path).suffix.lower()
        return ext_map.get(suffix, "unknown")
