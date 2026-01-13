# Trace Tool

A Python CLI tool that finds where files, jobs, or tables are used within your organization by searching code repositories (via Sourcegraph API) and file storage (AFS). Supports Kerberos SSO authentication and optional LLM-based impact summarization.

## Features

- 🔍 **Multi-source search**: Search both code repositories (Sourcegraph) and file storage (AFS)
- 🔐 **Kerberos SSO**: Secure authentication using Kerberos SSO
- 🤖 **LLM Summarization**: Optional AI-powered impact analysis
- 📊 **Multiple output formats**: Human-readable summaries or JSON
- ⚡ **Fast & parallelized**: Efficient search with configurable parallelism
- 🧪 **Tested**: Unit tests for core functionality

## Installation

### From source

```bash
git clone <repository-url>
cd ms-trace
pip install .
```

### Development installation

```bash
pip install -e ".[dev]"
```

## Configuration

1. Copy the example configuration file:

```bash
cp config.yaml.example config.yaml
```

2. Edit `config.yaml` with your settings:

```yaml
# Sourcegraph API Configuration
sourcegraph:
  endpoint: "https://sourcegraph.example.com/.api/graphql"
  token: ""  # Optional API token

# AFS Storage Configuration
afs:
  root_path: "/afs/project"
  search_patterns:
    - ".*\\.py$"
    - ".*\\.sql$"
    - ".*\\.ipynb$"

# Optional LLM Configuration
llm:
  enabled: false
  provider: "openai"
  model: "gpt-4"
  api_key: ""  # Or set via LLM_API_KEY environment variable
```

The configuration file is searched in the following order:
1. `config.yaml` in the current directory
2. `~/.trace/config.yaml`

## Usage

### Basic usage

```bash
# Search for a file
trace file.py

# Search for a job
trace job:daily_prices

# Search for a table
trace table:analytics.pnl
```

### Output formats

**Human-readable summary (default):**

```bash
trace file.py --summary
```

**JSON output:**

```bash
trace file.py --json
```

**Combined:**

```bash
trace file.py --summary --json
```

### Options

- `--json`: Output machine-readable JSON
- `--summary`: Generate human-readable summary (default if LLM enabled)
- `--depth N`: Limit search depth for cross-references (not yet implemented)
- `--config PATH`: Specify path to config.yaml file

## Examples

### Example 1: Finding file usage

```bash
$ trace pricing_engine.py

References for pricing_engine.py:

Code references:
  - airflow/dags/pricing.py (repo: trading, last modified: unknown, author: unknown)
  - notebooks/risk_report.ipynb (repo: analytics, last modified: unknown, author: unknown)

AFS references:
  - /afs/project/shared/scripts/pricing_engine.py (last modified: 2025-01-15T10:30:00)
  - /afs/project/legacy/old_pricing_engine.py (last modified: 2024-12-01T08:15:00)

Impact summary:
  - Found 2 code references and 2 AFS references
  - Risk level: UNKNOWN
```

### Example 2: JSON output with LLM summary

```bash
$ trace job:daily_prices --json

{
  "input": "job:daily_prices",
  "code_references": [
    {
      "path": "airflow/dags/daily_prices.py",
      "repo": "trading",
      "url": "https://sourcegraph.com/trading/airflow/dags/daily_prices.py",
      "last_modified": null,
      "author": null,
      "type": "code"
    }
  ],
  "afs_references": [
    {
      "path": "/afs/project/jobs/daily_prices.py",
      "last_modified": "2025-01-15T09:00:00",
      "type": "afs"
    }
  ],
  "impact_summary": "The daily_prices job is used in the trading repository...",
  "risk": "MEDIUM",
  "suggested_next_steps": [
    "Review downstream dependencies",
    "Test in staging environment",
    "Coordinate with trading team"
  ]
}
```

## Architecture

The tool is organized into modular components:

- `trace_cli.py`: CLI interface and argument parsing
- `search_sourcegraph.py`: Sourcegraph API integration with Kerberos SSO
- `search_afs.py`: AFS file system search with Kerberos authentication
- `summarize_impact.py`: Optional LLM-based impact summarization
- `config.py`: Configuration management

## Authentication

### Kerberos SSO

The tool uses `requests-kerberos` for Kerberos authentication. Ensure you have:

1. Valid Kerberos credentials (obtain via `kinit` if needed)
2. Properly configured Kerberos setup in your environment

The tool will automatically use Kerberos authentication for:
- Sourcegraph API requests
- AFS file system access

### API Tokens (optional)

Some Sourcegraph instances may require API tokens in addition to Kerberos. Set the token in `config.yaml`:

```yaml
sourcegraph:
  token: "your-api-token-here"
```

## LLM Integration

To enable LLM summarization:

1. Set `llm.enabled: true` in `config.yaml`
2. Set your API key via environment variable or config file:
   ```bash
   export LLM_API_KEY="your-api-key"
   ```
3. Configure provider and model (OpenAI is default)

The LLM will analyze code and file references to provide:
- Risk assessment (LOW, MEDIUM, HIGH)
- Impact summary
- Suggested next steps

## Development

### Running tests

```bash
pytest tests/
```

### Code structure

```
ms-trace/
├── trace/              # Main package
│   ├── __init__.py
│   ├── trace_cli.py    # CLI interface
│   ├── config.py       # Configuration
│   ├── search_sourcegraph.py
│   ├── search_afs.py
│   └── summarize_impact.py
├── tests/              # Unit tests
├── setup.py
├── requirements.txt
├── config.yaml.example
└── README.md
```

## Error Handling

The tool handles errors gracefully:

- **Network errors**: Automatic retries with exponential backoff
- **Missing files**: Warnings logged, tool continues
- **Permission errors**: Logged and skipped
- **API failures**: Errors logged, tool continues with available data

## Limitations

- Git blame information (author, last modified) requires additional Sourcegraph API calls and may not be available in all instances
- AFS search is read-only and respects file system permissions
- LLM summarization is optional and requires API access
- Search depth limiting (`--depth`) is planned but not yet implemented

## Troubleshooting

### Kerberos authentication issues

```bash
# Check Kerberos ticket
klist

# Obtain new ticket if needed
kinit username@REALM
```

### Sourcegraph API errors

- Verify the endpoint URL in `config.yaml`
- Check network connectivity
- Ensure Kerberos credentials are valid
- Check Sourcegraph API documentation for any schema changes

### AFS access issues

- Verify AFS is mounted and accessible
- Check file system permissions
- Ensure Kerberos credentials are valid for AFS access

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

