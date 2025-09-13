"""
Simple runner script for the RAG CLI tool.

Usage:
    python run_rag.py [repository_url]
    
Examples:
    python run_rag.py https://github.com/microsoft/vscode
    python run_rag.py ../test_repo
    python run_rag.py  # Will prompt for repository URL
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cli import RAGCLI


async def main():
    """Main function to run the RAG CLI."""
    cli = RAGCLI()
    
    # Get repository URL
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        repo_url = input("📁 Enter repository URL or path: ").strip()
        if not repo_url:
            print("No repository URL provided. Exiting.")
            return

    # Index the repository
    success = await cli.index_repository(repo_url)
    if not success:
        print("Failed to index repository. Exiting.")
        return

    # Start interactive mode
    await cli.interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)
