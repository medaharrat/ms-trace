"""CLI interface for trace tool."""

import json
import logging
import sys
from typing import Optional

import click
from traceit.config import Config
from traceit.search_afs import AFSSearcher
from traceit.search_gf import SourcegraphSearcher
from traceit.summarize_impact import ImpactSummarizer


def setup_logging(config: Config):
    """Set up logging configuration.

    Args:
        config: Configuration object
    """
    log_level = getattr(logging, config.get_log_level().upper(), logging.INFO)
    log_format = config.get(
        "logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def format_human_readable(
    query: str, code_refs: list, afs_refs: list, summary: Optional[dict] = None
) -> str:
    """Format results as human-readable text.

    Args:
        query: Original query
        code_refs: Code references
        afs_refs: AFS references
        summary: Optional impact summary

    Returns:
        Formatted string
    """
    output = [f"References for {query}:\n"]

    if code_refs:
        output.append("Code references:")
        for ref in code_refs:
            repo = ref.get("repo", "unknown")
            path = ref.get("path", "")
            last_mod = ref.get("last_modified", "unknown")
            author = ref.get("author", "unknown")
            output.append(
                f"  - {path} (repo: {repo}, last modified: {last_mod}, author: {author})"
            )
        output.append("")

    if afs_refs:
        output.append("AFS references:")
        for ref in afs_refs:
            path = ref.get("path", "")
            last_mod = ref.get("last_modified", "unknown")
            output.append(f"  - {path} (last modified: {last_mod})")
        output.append("")

    if summary:
        output.append("Impact summary:")
        output.append(f"  - {summary.get('impact_summary', 'N/A')}")
        output.append(f"  - Risk level: {summary.get('risk_level', 'UNKNOWN')}")

        next_steps = summary.get("suggested_next_steps", [])
        if next_steps:
            output.append("  - Suggested next steps:")
            for step in next_steps:
                output.append(f"    * {step}")

    return "\n".join(output)


def format_json(
    query: str, code_refs: list, afs_refs: list, summary: Optional[dict] = None
) -> str:
    """Format results as JSON.

    Args:
        query: Original query
        code_refs: Code references
        afs_refs: AFS references
        summary: Optional impact summary

    Returns:
        JSON string
    """
    result = {
        "input": query,
        "code_references": code_refs,
        "afs_references": afs_refs,
    }

    if summary:
        result["impact_summary"] = summary.get("impact_summary", "")
        result["risk"] = summary.get("risk_level", "UNKNOWN")
        result["suggested_next_steps"] = summary.get("suggested_next_steps", [])

    return json.dumps(result, indent=2)


@click.command()
@click.argument("query")
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
@click.option(
    "--summary",
    "generate_summary",
    is_flag=True,
    help="Generate human-readable summary (default)",
)
@click.option(
    "--depth",
    type=int,
    default=None,
    help="Limit search depth for cross-references",
)
@click.option("--config", type=click.Path(exists=True), help="Path to config.yaml file")
@click.option("--verbose", is_flag=True, help="Show all files analyzed (verbose mode)")
def main(
    query: str,
    output_json: bool,
    generate_summary: bool,
    depth: Optional[int],
    config: Optional[str],
    verbose: bool,
):
    """Trace file, job, or table usage across the organization.

    Examples:
        traceit file.py
        traceit job:daily_prices
        traceit table:analytics.pnl
    """
    # Load configuration
    cfg = Config(config_path=config)
    setup_logging(cfg)

    logger = logging.getLogger(__name__)
    logger.info(f"Tracing: {query}")

    # Initialize searchers
    sourcegraph_searcher = SourcegraphSearcher(
        endpoint=cfg.get_sourcegraph_endpoint(),
        token=cfg.get_sourcegraph_token(),
        timeout=cfg.get_request_timeout(),
        max_retries=cfg.get_max_retries(),
    )

    afs_searcher = AFSSearcher(
        root_path=cfg.get_afs_root_path(),
        search_patterns=cfg.get_afs_search_patterns(),
        verbose=verbose,
    )

    # Perform searches
    logger.info("Searching Sourcegraph...")
    code_refs = sourcegraph_searcher.search_references(query)

    logger.info("Searching AFS...")
    afs_refs = afs_searcher.search(query, max_depth=depth if depth else 1)

    # Generate summary if requested or for human-readable output
    summary = None
    should_generate_summary = generate_summary or not output_json

    if should_generate_summary:
        if cfg.is_llm_enabled():
            logger.info("Generating LLM summary...")
            llm_config = cfg.get_llm_config()
            summarizer = ImpactSummarizer(
                provider=llm_config.get("provider", "openai"),
                model=llm_config.get("model", "gpt-4"),
                api_key=llm_config.get("api_key"),
                base_url=llm_config.get("base_url"),
            )
            summary = summarizer.summarize(query, code_refs, afs_refs)
        else:
            # Generate basic summary without LLM
            summary = {
                "risk_level": "UNKNOWN",
                "impact_summary": f"Found {len(code_refs)} code references and {len(afs_refs)} AFS references",
                "suggested_next_steps": [],
            }

    # Output results
    if output_json:
        print(format_json(query, code_refs, afs_refs, summary))
    else:
        print(format_human_readable(query, code_refs, afs_refs, summary))


if __name__ == "__main__":
    main()
