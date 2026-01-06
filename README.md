<p align="center">
  <img src="logo.svg" alt="Detective Benno Logo" width="120" height="120">
</p>

<h1 align="center">Detective Benno</h1>

[![Python Version](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=flat&logo=openai&logoColor=white)](https://openai.com/)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-D4A574?style=flat&logo=anthropic&logoColor=white)](https://anthropic.com/)
[![Groq](https://img.shields.io/badge/Groq-LPU--Inference-F55036?style=flat&logo=groq&logoColor=white)](https://groq.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Models-000000?style=flat&logo=llama&logoColor=white)](https://ollama.ai/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF?style=flat&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)](https://github.com/bimakw/detective-benno)

> *"Every line of code tells a story. I find the plot holes."* - Detective Benno

An intelligent code review detective powered by LLM that investigates your pull requests and uncovers bugs, security vulnerabilities, and code smells before they become problems.

## Features

- **Multi-LLM Provider Support** - Use OpenAI, Anthropic Claude, Groq, or local models via Ollama (codellama, deepseek-coder, mistral)
- **Automated PR Investigation** - Automatically triggered on pull request events
- **Inline PR Comments** - Posts findings directly on relevant code lines
- **Multi-language Support** - Investigates Python, Go, JavaScript, TypeScript, Rust, and more
- **Configurable Rules** - Define custom investigation guidelines per repository
- **GitHub Action** - Easy integration with existing CI/CD pipelines
- **CLI Tool** - Investigate local changes before committing
- **Diff-aware Analysis** - Only investigates changed code, not entire files

## Quick Start

### Installation

```bash
pip install detective-benno
```

### CLI Usage

```bash
# Investigate specific files
benno investigate src/main.py src/utils.py

# Investigate staged changes
benno staged

# Investigate a git diff (pipe to stdin)
git diff main..feature | benno diff

# Investigate with custom guidelines
benno investigate --config .benno.yaml src/

# Use Ollama for local models (free!)
benno investigate --provider ollama --model codellama src/main.py

# Initialize config file
benno init
```

### Using Different Providers

#### OpenAI (Default)
```bash
export OPENAI_API_KEY=your-api-key
benno investigate src/main.py
```

#### Anthropic Claude
```bash
export ANTHROPIC_API_KEY=your-api-key
benno investigate --provider anthropic src/main.py

# Use specific Claude model
benno investigate --provider anthropic --model claude-sonnet-4-20250514 src/main.py
```

#### Groq (Fast Inference)
```bash
export GROQ_API_KEY=your-api-key
benno investigate --provider groq src/main.py

# Use specific Groq model
benno investigate --provider groq --model llama-3.3-70b-versatile src/main.py
benno investigate --provider groq --model mixtral-8x7b-32768 src/main.py
```

#### Ollama (Local Models - Free!)
First, install and start Ollama:
```bash
# Install Ollama (https://ollama.ai)
ollama pull codellama  # or deepseek-coder, mistral
```

Then use it with Detective Benno:
```bash
benno investigate --provider ollama --model codellama src/main.py

# Or set defaults in config
benno init  # Creates .benno.yaml
```

### GitHub Action

Add to your `.github/workflows/detective-benno.yml`:

```yaml
name: Detective Benno Investigation

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  investigate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detective Benno Investigation
        uses: bimakw/detective-benno@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          investigation_level: detailed  # minimal, standard, detailed
          post_inline_comments: true      # Post comments on code lines
          post_summary_comment: true      # Post summary comment
```

#### Using Ollama in GitHub Actions

```yaml
- name: Start Ollama
  run: |
    curl -fsSL https://ollama.ai/install.sh | sh
    ollama pull codellama &

- name: Detective Benno Investigation
  uses: bimakw/detective-benno@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    provider: ollama
    model: codellama
```

## Configuration

Create `.benno.yaml` in your repository root:

```yaml
# Detective Benno Configuration
version: "1"

# Provider settings
provider:
  name: openai         # openai, anthropic, groq, or ollama
  model: gpt-4o        # gpt-4o, claude-sonnet-4-20250514, llama-3.3-70b-versatile, codellama, etc.
  base_url: null       # For Ollama: http://localhost:11434

# Investigation settings
investigation:
  level: detailed          # minimal, standard, detailed
  max_findings: 10         # Maximum findings per investigation
  languages:               # Language-specific settings
    python:
      style_guide: pep8
      check_types: true
    go:
      style_guide: effective-go
    javascript:
      style_guide: airbnb

# Custom investigation guidelines
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
  patterns:
    - "TODO:"  # Don't flag TODOs
```

## Investigation Categories

Detective Benno investigates for:

| Category | Description |
|----------|-------------|
| **Security** | SQL injection, XSS, hardcoded secrets, unsafe operations |
| **Performance** | N+1 queries, unnecessary loops, memory leaks |
| **Best Practices** | Code style, naming conventions, design patterns |
| **Error Handling** | Missing try-catch, unhandled promises, panic recovery |
| **Maintainability** | Code duplication, complexity, documentation |

## Example Investigation Report

```
============================================
   DETECTIVE BENNO - INVESTIGATION REPORT
============================================

Case #: PR-142
Files Investigated: 3
Findings: 5 (2 critical, 2 warnings, 1 suggestion)

CRITICAL FINDINGS
-----------------

Location: src/auth.py:45
Evidence:
   query = f"SELECT * FROM users WHERE id = {user_id}"

Finding: Potential SQL injection vulnerability
Recommendation: Use parameterized queries instead:
   query = "SELECT * FROM users WHERE id = %s"
   cursor.execute(query, (user_id,))

WARNINGS
--------

Location: src/api.py:128
Finding: Function `process_data` exceeds 50 lines
Recommendation: Consider breaking into smaller functions

============================================
Case Status: REQUIRES ATTENTION
============================================
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For OpenAI | Your OpenAI API key |
| `ANTHROPIC_API_KEY` | For Anthropic | Your Anthropic API key |
| `GROQ_API_KEY` | For Groq | Your Groq API key |
| `OLLAMA_HOST` | No | Ollama server URL (default: http://localhost:11434) |
| `GITHUB_TOKEN` | For PR investigations | GitHub token with PR write access |
| `BENNO_CONFIG` | No | Path to custom config file |

## Development

```bash
# Clone repository
git clone https://github.com/bimakw/detective-benno.git
cd detective-benno

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/detective_benno --cov-report=term-missing

# Run linting
ruff check .
mypy src/
```

## Project Structure

```
detective-benno/
├── src/detective_benno/
│   ├── __init__.py
│   ├── cli.py                # CLI commands
│   ├── config.py             # Configuration loading
│   ├── models.py             # Pydantic models
│   ├── prompts.py            # LLM prompts
│   ├── reviewer.py           # Core review logic
│   ├── providers/            # LLM providers
│   │   ├── base.py           # Abstract provider
│   │   ├── openai.py         # OpenAI implementation
│   │   ├── anthropic.py      # Anthropic Claude implementation
│   │   ├── groq.py           # Groq implementation
│   │   ├── ollama.py         # Ollama implementation
│   │   └── factory.py        # Provider factory
│   └── github/               # GitHub integration
│       ├── api.py            # GitHub API wrapper
│       └── inline_comments.py # PR inline comments
├── tests/                    # Test suite (87% coverage)
├── action.yml                # GitHub Action definition
└── pyproject.toml
```

## Why "Detective Benno"?

Every codebase has mysteries waiting to be solved - bugs hiding in plain sight, security vulnerabilities lurking in the shadows, and performance bottlenecks slowing everything down. Detective Benno is your tireless investigator, examining every line of code to uncover issues before they become problems.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT-4 API
- Anthropic for Claude API
- Groq for fast LPU inference
- Ollama for local LLM support
- GitHub Actions for CI/CD integration
- The open source community

---

<p align="center">
  <strong>Detective Benno - Solving code mysteries, one PR at a time</strong>
  <br>
  <sub>Made with code by <a href="https://github.com/bimakw">Bima Kharisma Wicaksana</a></sub>
</p>
