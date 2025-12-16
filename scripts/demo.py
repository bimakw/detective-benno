#!/usr/bin/env python3
"""Demo script for Detective Benno - simulates investigation output."""

import time
import sys

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

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

def slow_print(text: str, delay: float = 0.03):
    """Print text character by character."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def demo():
    """Run the demo."""
    # Banner
    console.print(BANNER)
    time.sleep(1)

    # Simulating file scan
    console.print("\n[dim]Investigating files...[/dim]")
    time.sleep(0.5)

    files = ["src/auth.py", "src/api.py", "src/database.py"]
    for f in files:
        console.print(f"  [cyan]→[/cyan] {f}")
        time.sleep(0.3)

    time.sleep(0.5)
    console.print("\n[dim]Analyzing code with GPT-4o...[/dim]")
    time.sleep(1.5)

    # Investigation Report
    console.print()
    console.print(
        Panel(
            "[bold]Files Investigated:[/bold] 3\n"
            "[bold]Findings:[/bold] 4 "
            "([red]2 critical[/red], "
            "[yellow]1 warning[/yellow], "
            "[blue]1 suggestion[/blue])",
            title="INVESTIGATION REPORT",
            border_style="cyan",
        )
    )

    time.sleep(0.5)

    # Critical findings
    console.print("\n[bold red]CRITICAL FINDINGS[/bold red]")
    console.print("[red]" + "─" * 40 + "[/red]")

    time.sleep(0.3)
    console.print(
        "\n[red]Location:[/red] [bold]src/auth.py:45[/bold] [dim](security)[/dim]"
    )
    console.print("[red]Finding:[/red] Potential SQL injection vulnerability")
    console.print("[red]Recommendation:[/red] Use parameterized queries")

    code = '''# Before (vulnerable)
query = f"SELECT * FROM users WHERE id = {user_id}"

# After (safe)
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))'''

    time.sleep(0.3)
    syntax = Syntax(code, "python", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="Suggested fix", border_style="green"))

    time.sleep(0.5)
    console.print(
        "\n[red]Location:[/red] [bold]src/auth.py:78[/bold] [dim](security)[/dim]"
    )
    console.print("[red]Finding:[/red] Hardcoded secret key detected")
    console.print("[red]Recommendation:[/red] Use environment variables for secrets")

    time.sleep(0.5)

    # Warnings
    console.print("\n[bold yellow]WARNINGS[/bold yellow]")
    console.print("[yellow]" + "─" * 40 + "[/yellow]")

    time.sleep(0.3)
    console.print(
        "\n[yellow]Location:[/yellow] [bold]src/api.py:128[/bold] [dim](performance)[/dim]"
    )
    console.print("[yellow]Finding:[/yellow] N+1 query detected in loop")
    console.print("[yellow]Recommendation:[/yellow] Use batch query or eager loading")

    time.sleep(0.5)

    # Suggestions
    console.print("\n[bold blue]SUGGESTIONS[/bold blue]")
    console.print("[blue]" + "─" * 40 + "[/blue]")

    time.sleep(0.3)
    console.print(
        "\n[blue]Location:[/blue] [bold]src/database.py:15[/bold] [dim](maintainability)[/dim]"
    )
    console.print("[blue]Finding:[/blue] Function exceeds 50 lines")
    console.print("[blue]Recommendation:[/blue] Consider breaking into smaller functions")

    time.sleep(0.5)

    # Case status
    console.print("\n[bold red]Case Status: REQUIRES IMMEDIATE ATTENTION[/bold red]")
    console.print()


if __name__ == "__main__":
    demo()
