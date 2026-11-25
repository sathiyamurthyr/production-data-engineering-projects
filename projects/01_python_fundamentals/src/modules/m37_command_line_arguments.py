"""
================================================================================
MODULE 37: Command Line Arguments & CLI Parser
================================================================================
1. EXPLANATION:
`argparse` parses command line flags (`--env`, `--batch-size`, `--input-path`) passed by orchestrators.

2. BUSINESS USE CASE:
Parse pipeline execution parameters from command line interface.
"""
import argparse

def parse_pipeline_args(args_list=None):
    """Parse CLI arguments for pipeline execution."""
    parser = argparse.ArgumentParser(description="Data Engineering Pipeline CLI")
    parser.add_argument("--env", default="development", help="Execution environment")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch processing size")
    return parser.parse_args(args_list)

if __name__ == "__main__":
    cli_args = parse_pipeline_args(["--env", "production", "--batch-size", "500"])
    print(f"Parsed CLI Args: ENV={cli_args.env}, BatchSize={cli_args.batch_size}")
