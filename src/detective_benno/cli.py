"""Command-line interface for Detective Benno."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from detective_benno.config import load_config
from detective_benno.models import ReviewResult, Severity
from detective_benno.reviewer import CodeReviewer

console = Console()

BANNER = r"""
[bold cyan]
    ____       __            __  _            ____
   / __ \___  / /____  _____/ /_(_)   _____  / __ )___  ____  ____  ____
  / / / / _ \/ __/ _ \/ ___/ __/ / | / / _ \/ __  / _ \/ __ \/ __ \/ __ \
 / /_/ /  __/ /_/  __/ /__/ /_/ /| |/ /  __/ /_/ /  __/ / / / / / / /_/ /
/_____/\___/\__/\___/\___/\__/_/ |___/\___/_____/\___/_/ /_/_/ /_/\____/
[/bold cyan]
[dim]Solving code mysteries, one PR at a time[/dim]
"""


# Common options for review commands
def common_options(f):
    """Decorator for common review options."""
    f = click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")(f)
    f = click.option("--provider", "-p", type=click.Choice(["openai", "ollama", "anthropic", "groq"]),
                     help="LLM provider to use (overrides config)")(f)
    f = click.option("--model", "-m", help="Model to use (e.g., gpt-4o, codellama)")(f)
    f = click.option("--level", type=click.Choice(["minimal", "standard", "detailed"]),
                     default="standard", help="Investigation detail level")(f)
    f = click.option("--json", "output_json", is_flag=True, help="Output as JSON")(f)
    f = click.option("--quiet", "-q", is_flag=True, help="Suppress banner")(f)
    return f


def _setup_reviewer(config_path, provider, model, level, quiet, output_json) -> tuple[CodeReviewer, bool, bool]:
    """Setup reviewer with config, return (reviewer, quiet, output_json)."""
    review_config = load_config(config_path)
    review_config.level = level

    # Override provider settings from CLI flags
    if provider:
        review_config.provider.name = provider
    if model:
        review_config.provider.model = model
        review_config.model = model

    # Show provider info
    if not quiet and not output_json:
        console.print(BANNER)
        provider_name = review_config.provider.name
        model_name = review_config.provider.effective_model
        console.print(f"[dim]Using {provider_name} with {model_name}[/dim]\n")

    return CodeReviewer(config=review_config), quiet, output_json


def _handle_result(result: ReviewResult, output_json: bool) -> None:
    """Handle review result output and exit code."""
    if output_json:
        _output_json(result)
    else:
        _output_report(result)

    if result.has_critical_issues:
        sys.exit(1)


@click.group()
def main():
    """Detective Benno - Code review detective powered by LLM.

    Investigate code changes to uncover bugs, security issues, and
    code smells before they become problems.

    Commands:

        benno FILES...            Review specific files/directories

        benno --staged            Review staged git changes

        benno --diff              Review diff from stdin

        benno init                Create configuration file

        benno version             Show version information

    Examples:

        benno src/main.py src/utils.py

        benno --provider ollama --model codellama src/

        git diff main..feature | benno --diff
    """
    pass


@main.command(name="investigate")
@common_options
@click.argument("files", nargs=-1, required=True, type=click.Path())
def investigate_cmd(
    files: tuple[str, ...],
    config: str | None,
    provider: str | None,
    model: str | None,
    level: str,
    output_json: bool,
    quiet: bool,
) -> None:
    """Investigate specific files or directories."""
    reviewer, quiet, output_json = _setup_reviewer(config, provider, model, level, quiet, output_json)

    try:
        result = _investigate_files(reviewer, list(files))
        _handle_result(result, output_json)
    except Exception as e:
        console.print(f"[red]Investigation failed:[/red] {e}")
        sys.exit(1)


# Make "benno FILES" work directly (default command)
@main.command(name="files", hidden=True)
@common_options
@click.argument("files", nargs=-1, required=True, type=click.Path())
def files_cmd(
    files: tuple[str, ...],
    config: str | None,
    provider: str | None,
    model: str | None,
    level: str,
    output_json: bool,
    quiet: bool,
) -> None:
    """Investigate specific files (hidden, same as investigate)."""
    reviewer, quiet, output_json = _setup_reviewer(config, provider, model, level, quiet, output_json)

    try:
        result = _investigate_files(reviewer, list(files))
        _handle_result(result, output_json)
    except Exception as e:
        console.print(f"[red]Investigation failed:[/red] {e}")
        sys.exit(1)


@main.command(name="staged")
@common_options
def staged_cmd(
    config: str | None,
    provider: str | None,
    model: str | None,
    level: str,
    output_json: bool,
    quiet: bool,
) -> None:
    """Investigate staged git changes."""
    reviewer, quiet, output_json = _setup_reviewer(config, provider, model, level, quiet, output_json)

    try:
        result = _investigate_staged_changes(reviewer)
        _handle_result(result, output_json)
    except Exception as e:
        console.print(f"[red]Investigation failed:[/red] {e}")
        sys.exit(1)


@main.command(name="diff")
@common_options
def diff_cmd(
    config: str | None,
    provider: str | None,
    model: str | None,
    level: str,
    output_json: bool,
    quiet: bool,
) -> None:
    """Investigate diff from stdin.

    Example: git diff main..feature | benno diff
    """
    reviewer, quiet, output_json = _setup_reviewer(config, provider, model, level, quiet, output_json)

    try:
        diff_content = sys.stdin.read()
        if not diff_content.strip():
            console.print("[yellow]No diff content to investigate[/yellow]")
            sys.exit(0)
        result = reviewer.review_diff(diff_content)
        _handle_result(result, output_json)
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
        if not p.exists():
            console.print(f"[red]Path not found:[/red] {path}")
            sys.exit(1)

        if p.is_file():
            try:
                files.append(
                    FileChange(
                        path=str(p),
                        content=p.read_text(),
                        language=reviewer._detect_language(str(p)),
                    )
                )
            except Exception as e:
                console.print(f"[yellow]Skipping {path}:[/yellow] {e}")
        elif p.is_dir():
            for file in p.rglob("*"):
                if file.is_file() and not _is_binary(file):
                    try:
                        files.append(
                            FileChange(
                                path=str(file),
                                content=file.read_text(),
                                language=reviewer._detect_language(str(file)),
                            )
                        )
                    except (OSError, UnicodeDecodeError):
                        # Skip files that can't be read (binary, permissions, etc.)
                        continue

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

    if result.has_critical_issues:
        console.print("\n[bold red]Case Status: REQUIRES IMMEDIATE ATTENTION[/bold red]")
    elif result.warning_count > 0:
        console.print("\n[bold yellow]Case Status: REQUIRES ATTENTION[/bold yellow]")
    else:
        console.print("\n[bold green]Case Status: MINOR ISSUES[/bold green]")

    console.print()


@main.command()
@click.option("--global", "is_global", is_flag=True, help="Create global config")
def init(is_global: bool) -> None:
    """Initialize configuration file."""
    config_content = """# Detective Benno Configuration
version: "1"

# Investigation settings
investigation:
  level: standard          # minimal, standard, detailed
  max_findings: 10         # Maximum findings per investigation

# Provider settings
# Supported providers: openai, ollama
provider:
  name: openai             # openai or ollama
  model: gpt-4o            # Model name (provider-specific)
  # api_key: xxx           # Optional: falls back to OPENAI_API_KEY env var
  # base_url: http://...   # Optional: for Ollama or custom endpoints
  temperature: 0.3

# Ollama example (uncomment to use):
# provider:
#   name: ollama
#   model: codellama       # or: deepseek-coder, mistral, llama3
#   base_url: http://localhost:11434

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
