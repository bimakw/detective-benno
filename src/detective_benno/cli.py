"""Command-line interface for Detective Benno."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from detective_benno.config import load_config
from detective_benno.models import ReviewResult, Severity
from detective_benno.reviewer import CodeReviewer

console = Console()

BANNER = """
[bold cyan]
    ____       __            __  _            ____
   / __ \___  / /____  _____/ /_(_)   _____  / __ )___  ____  ____  ____
  / / / / _ \/ __/ _ \/ ___/ __/ / | / / _ \/ __  / _ \/ __ \/ __ \/ __ \\
 / /_/ /  __/ /_/  __/ /__/ /_/ /| |/ /  __/ /_/ /  __/ / / / / / / /_/ /
/_____/\___/\__/\___/\___/\__/_/ |___/\___/_____/\___/_/ /_/_/ /_/\____/
[/bold cyan]
[dim]Solving code mysteries, one PR at a time[/dim]
"""


@click.group(invoke_without_command=True)
@click.option(
    "--staged", is_flag=True, help="Investigate staged git changes"
)
@click.option(
    "--diff", is_flag=True, help="Read diff from stdin"
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to config file"
)
@click.option(
    "--level",
    type=click.Choice(["minimal", "standard", "detailed"]),
    default="standard",
    help="Investigation detail level",
)
@click.option(
    "--json", "output_json", is_flag=True, help="Output as JSON"
)
@click.option(
    "--quiet", "-q", is_flag=True, help="Suppress banner"
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def main(
    ctx: click.Context,
    staged: bool,
    diff: bool,
    config: Optional[str],
    level: str,
    output_json: bool,
    quiet: bool,
    files: tuple[str, ...],
) -> None:
    """Detective Benno - Code review detective powered by LLM.

    Investigate code changes to uncover bugs, security issues, and
    code smells before they become problems.

    Examples:

        # Investigate specific files
        benno src/main.py src/utils.py

        # Investigate staged git changes
        benno --staged

        # Investigate from diff
        git diff main..feature | benno --diff

        # Use custom config
        benno --config .benno.yaml src/
    """
    if ctx.invoked_subcommand is not None:
        return

    if not quiet and not output_json:
        console.print(BANNER)

    review_config = load_config(config)
    review_config.level = level

    reviewer = CodeReviewer(config=review_config)

    try:
        if diff:
            diff_content = sys.stdin.read()
            result = reviewer.review_diff(diff_content)
        elif staged:
            result = _investigate_staged_changes(reviewer)
        elif files:
            result = _investigate_files(reviewer, list(files))
        else:
            click.echo(ctx.get_help())
            return

        if output_json:
            _output_json(result)
        else:
            _output_report(result)

        # Exit with error code if critical issues found
        if result.has_critical_issues:
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Investigation failed:[/red] {e}")
        sys.exit(1)


def _investigate_staged_changes(reviewer: CodeReviewer) -> ReviewResult:
    """Investigate staged git changes."""
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
        check=True,
    )

    if not result.stdout.strip():
        console.print("[yellow]No staged changes to investigate[/yellow]")
        sys.exit(0)

    return reviewer.review_diff(result.stdout)


def _investigate_files(reviewer: CodeReviewer, paths: list[str]) -> ReviewResult:
    """Investigate specified files."""
    from detective_benno.models import FileChange

    files = []
    for path in paths:
        p = Path(path)
        if p.is_file():
            files.append(
                FileChange(
                    path=str(p),
                    content=p.read_text(),
                    language=reviewer._detect_language(str(p)),
                )
            )
        elif p.is_dir():
            for file in p.rglob("*"):
                if file.is_file() and not _is_binary(file):
                    files.append(
                        FileChange(
                            path=str(file),
                            content=file.read_text(),
                            language=reviewer._detect_language(str(file)),
                        )
                    )

    if not files:
        console.print("[yellow]No files to investigate[/yellow]")
        sys.exit(0)

    return reviewer.review_files(files)


def _is_binary(path: Path) -> bool:
    """Check if a file is binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        return True


def _output_json(result: ReviewResult) -> None:
    """Output result as JSON."""
    import json

    print(json.dumps(result.model_dump(), indent=2))


def _output_report(result: ReviewResult) -> None:
    """Output investigation report with rich formatting."""
    console.print()
    console.print(
        Panel(
            f"[bold]Files Investigated:[/bold] {result.files_reviewed}\n"
            f"[bold]Findings:[/bold] {len(result.comments)} "
            f"([red]{result.critical_count} critical[/red], "
            f"[yellow]{result.warning_count} warnings[/yellow], "
            f"[blue]{result.suggestion_count} suggestions[/blue])",
            title="INVESTIGATION REPORT",
            border_style="cyan",
        )
    )

    if not result.comments:
        console.print("\n[green]Case closed - No issues found![/green]")
        return

    # Group by severity
    severity_order = [Severity.CRITICAL, Severity.WARNING, Severity.SUGGESTION, Severity.INFO]
    severity_styles = {
        Severity.CRITICAL: ("red", "CRITICAL FINDINGS"),
        Severity.WARNING: ("yellow", "WARNINGS"),
        Severity.SUGGESTION: ("blue", "SUGGESTIONS"),
        Severity.INFO: ("dim", "INFO"),
    }

    for severity in severity_order:
        comments = [c for c in result.comments if c.severity == severity]
        if not comments:
            continue

        style, title = severity_styles[severity]
        console.print(f"\n[bold {style}]{title}[/bold {style}]")
        console.print(f"[{style}]{'─' * 40}[/{style}]")

        for comment in comments:
            console.print(
                f"\n[{style}]Location:[/{style}] "
                f"[bold]{comment.file_path}:{comment.line_range}[/bold] "
                f"[dim]({comment.category})[/dim]"
            )
            console.print(f"[{style}]Finding:[/{style}] {comment.message}")

            if comment.suggestion:
                console.print(f"[{style}]Recommendation:[/{style}] {comment.suggestion}")

            if comment.suggested_code:
                syntax = Syntax(
                    comment.suggested_code,
                    "python",
                    theme="monokai",
                    line_numbers=False,
                )
                console.print(Panel(syntax, title="Suggested fix", border_style="green"))

    # Case status
    if result.has_critical_issues:
        console.print("\n[bold red]Case Status: REQUIRES IMMEDIATE ATTENTION[/bold red]")
    elif result.warning_count > 0:
        console.print("\n[bold yellow]Case Status: REQUIRES ATTENTION[/bold yellow]")
    else:
        console.print("\n[bold green]Case Status: MINOR ISSUES[/bold green]")

    console.print()


@main.command()
@click.option(
    "--global", "is_global", is_flag=True, help="Create global config"
)
def init(is_global: bool) -> None:
    """Initialize configuration file."""
    config_content = """# Detective Benno Configuration
version: "1"

# Investigation settings
investigation:
  level: standard          # minimal, standard, detailed
  max_findings: 10         # Maximum findings per investigation

# Custom investigation guidelines (add your own)
guidelines:
  - "Look for potential SQL injection vulnerabilities"
  - "Check for hardcoded credentials or secrets"
  - "Verify error handling is comprehensive"
  - "Ensure all functions have proper documentation"

# Ignore patterns
ignore:
  files:
    - "*.md"
    - "*.txt"
    - "vendor/**"
    - "node_modules/**"

# Model settings
model:
  provider: openai
  name: gpt-4o
  temperature: 0.3
"""

    if is_global:
        config_path = Path.home() / ".config" / "detective-benno" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        config_path = Path(".benno.yaml")

    if config_path.exists():
        if not click.confirm(f"{config_path} already exists. Overwrite?"):
            return

    config_path.write_text(config_content)
    console.print(f"[green]Case file created:[/green] {config_path}")


@main.command()
def version() -> None:
    """Show version information."""
    from detective_benno import __version__

    console.print(f"[cyan]Detective Benno[/cyan] v{__version__}")
    console.print("[dim]Solving code mysteries, one PR at a time[/dim]")


if __name__ == "__main__":
    main()
