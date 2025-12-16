"""Core investigation engine for Detective Benno."""

import json
from pathlib import Path
from typing import Optional

from openai import OpenAI

from detective_benno.models import (
    FileChange,
    ReviewComment,
    ReviewConfig,
    ReviewResult,
    Severity,
)
from detective_benno.prompts import build_review_prompt


class CodeReviewer:
    """AI-powered code investigator using OpenAI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[ReviewConfig] = None,
    ) -> None:
        """Initialize the code investigator.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            config: Investigation configuration. Uses defaults if not provided.
        """
        self.client = OpenAI(api_key=api_key)
        self.config = config or ReviewConfig()

    def review_files(self, files: list[FileChange]) -> ReviewResult:
        """Investigate multiple files and return aggregated results.

        Args:
            files: List of file changes to investigate.

        Returns:
            Aggregated investigation result.
        """
        all_comments: list[ReviewComment] = []
        total_tokens = 0

        for file in files:
            if self._should_ignore_file(file.path):
                continue

            result = self._review_single_file(file)
            all_comments.extend(result.comments)
            total_tokens += result.tokens_used

        return ReviewResult(
            files_reviewed=len(files),
            comments=all_comments[: self.config.max_comments],
            model_used=self.config.model,
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

    def review_file(self, path: str, content: Optional[str] = None) -> ReviewResult:
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
        prompt = build_review_prompt(
            file=file,
            config=self.config,
        )

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
        )

        tokens_used = response.usage.total_tokens if response.usage else 0
        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
            comments = self._parse_review_response(data, file.path)
        except json.JSONDecodeError:
            comments = []

        return ReviewResult(
            files_reviewed=1,
            comments=comments,
            tokens_used=tokens_used,
            model_used=self.config.model,
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

    def _parse_review_response(
        self, data: dict, file_path: str
    ) -> list[ReviewComment]:
        """Parse the AI response into ReviewComment objects."""
        comments = []
        for item in data.get("comments", []):
            try:
                comment = ReviewComment(
                    file_path=file_path,
                    line_start=item.get("line_start", 1),
                    line_end=item.get("line_end"),
                    severity=Severity(item.get("severity", "suggestion")),
                    category=item.get("category", "best-practice"),
                    message=item.get("message", ""),
                    suggestion=item.get("suggestion"),
                    suggested_code=item.get("suggested_code"),
                )
                comments.append(comment)
            except (ValueError, KeyError):
                continue
        return comments

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
        current_diff_lines = []

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
