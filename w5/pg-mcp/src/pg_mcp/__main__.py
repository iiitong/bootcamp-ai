"""Entry point for running the MCP server.

Usage:
    # Run the server (default)
    python -m pg_mcp

    # Validate configuration file
    python -m pg_mcp config validate --config /path/to/config.yaml
"""

import argparse
import sys


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pg-mcp",
        description="PostgreSQL MCP Server with natural language query support",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management commands",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        help="Config commands",
    )

    # config validate subcommand
    validate_parser = config_subparsers.add_parser(
        "validate",
        help="Validate a configuration file",
    )
    validate_parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the configuration file to validate",
    )

    return parser


def main() -> None:
    """Entry point for the MCP server."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "config":
        if args.config_command == "validate":
            # Import here to avoid loading server dependencies for config validation
            from pg_mcp.config.validators import validate_config_command

            exit_code = validate_config_command(args.config)
            sys.exit(exit_code)
        else:
            parser.parse_args(["config", "--help"])
    elif args.command is None:
        # Default: run the server
        from pg_mcp.server import main as server_main

        server_main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
