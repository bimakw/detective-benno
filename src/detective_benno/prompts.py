"""Prompt templates for Detective Benno."""

from detective_benno.models import FileChange, ReviewConfig


def build_review_prompt(file: FileChange, config: ReviewConfig) -> str:
    """Build the investigation prompt for a file.

    Args:
        file: The file change to investigate.
        config: Investigation configuration.

    Returns:
        Formatted prompt string.
    """
    level_instructions = {
        "minimal": "Focus only on critical security issues and obvious bugs.",
        "standard": "Investigate for security, performance, and best practices.",
        "detailed": "Conduct comprehensive investigation including style, documentation, and potential improvements.",
    }

    instruction = level_instructions.get(config.level, level_instructions["standard"])

    prompt_parts = [
        f"Investigate the following {file.language or 'code'} file: `{file.path}`",
        f"\nInvestigation level: {config.level}",
        f"Instructions: {instruction}",
    ]

    if file.diff:
        prompt_parts.append(f"\n## Diff\n```diff\n{file.diff}\n```")
    elif file.content:
        prompt_parts.append(f"\n## Full Content\n```{file.language or ''}\n{file.content}\n```")

    prompt_parts.append(
        "\nProvide your findings as a JSON object with a 'comments' array."
    )

    return "\n".join(prompt_parts)


def build_summary_prompt(file_count: int, comment_count: int) -> str:
    """Build prompt for generating investigation summary.

    Args:
        file_count: Number of files investigated.
        comment_count: Number of findings generated.

    Returns:
        Summary prompt.
    """
    return f"""Generate a brief summary of this code investigation.
Files investigated: {file_count}
Findings: {comment_count}

Provide a 2-3 sentence summary highlighting the most important discoveries."""
