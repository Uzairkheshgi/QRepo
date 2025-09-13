"""
RAG CLI Tool for Repository Indexing and Q&A

A simple command-line interface for indexing GitHub repositories
and asking questions about codebases using RAG technology.
"""

import asyncio
import logging
import sys
from typing import Optional

from dotenv import load_dotenv

from services.rag_service import RAGService
from services.repository_service import RepositoryService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class RAGCLI:
    """Command-line interface for RAG repository indexing and Q&A."""

    def __init__(self):
        """Initialize the CLI with required services."""
        self.repository_service = RepositoryService()
        self.rag_service = RAGService()
        self.current_session_id: Optional[str] = None
        self.is_indexed = False

    async def index_repository(self, repo_url: str) -> bool:
        """
        Index a repository for Q&A.

        Args:
            repo_url: URL or path of the repository to index

        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            # Generate session ID based on repo URL
            session_id = f"session-{hash(repo_url) % 10000}"
            self.current_session_id = session_id

            logger.info(f"Indexing repository: {repo_url}")
            logger.info("=" * 60)

            # Step 1: Clone repository
            logger.info("Cloning repository...")
            repo_path = await self.repository_service.clone_repository(
                repo_url, session_id
            )
            logger.info(f"Repository cloned to: {repo_path}")

            # Step 2: Process files
            logger.info("Processing files...")
            files = await self.repository_service.process_repository_files(repo_path)
            logger.info(f"Processed {len(files)} files")

            # Step 3: Create vector index
            logger.info("Creating vector embeddings...")
            await self.rag_service.create_index(session_id, files, repo_url)
            logger.info("Vector index created successfully")

            self.is_indexed = True
            logger.info("Repository indexed successfully!")
            logger.info("You can now ask questions about the codebase.")
            return True

        except Exception as e:
            logger.error(f"Error indexing repository: {str(e)}")
            logger.error(f"Failed to index repository: {str(e)}")
            return False

    async def ask_question(self, question: str) -> bool:
        """
        Ask a question about the indexed repository.

        Args:
            question: The question to ask

        Returns:
            True if question was answered successfully, False otherwise
        """
        if not self.is_indexed or not self.current_session_id:
            logger.error("No repository indexed. Please index a repository first.")
            return False

        try:
            logger.info(f"Question: {question}")
            logger.info("Thinking...")

            response = await self.rag_service.query(self.current_session_id, question)

            if response:
                logger.info("Answer:")
                logger.info(f"{response['answer']}")
                logger.info(
                    f"Confidence: {response.get('confidence', 'unknown').upper()}"
                )
                logger.info(f"Sources: {len(response.get('sources', []))} files")

                # Show source files
                if response.get("sources"):
                    logger.info("Source files:")
                    for i, source in enumerate(
                        response["sources"][:3], 1
                    ):  # Show first 3 sources
                        logger.info(f"  {i}. {source['file']}")
                    if len(response["sources"]) > 3:
                        logger.info(
                            f"  ... and {len(response['sources']) - 3} more files"
                        )

                return True
            else:
                logger.error("Failed to get answer")
                return False

        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            logger.error(f"Error processing question: {str(e)}")
            return False

    async def interactive_mode(self):
        """Start interactive Q&A mode."""
        if not self.is_indexed:
            logger.error("No repository indexed. Please index a repository first.")
            return

        logger.info("=" * 60)
        logger.info("Interactive Q&A Mode")
        logger.info("=" * 60)
        logger.info(
            "Ask questions about the codebase. Type 'quit', 'exit', or 'q' to stop."
        )
        logger.info("Type 'help' for example questions.")

        while True:
            try:
                question = input("Your question: ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    logger.info("Goodbye!")
                    break
                elif not question:
                    logger.info("Please enter a question.")
                    continue

                await self.ask_question(question)

            except KeyboardInterrupt:
                logger.info("Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")


async def main():
    """Main CLI function."""
    logger.info("RAG Repository Indexer and Q&A Tool")
    logger.info("=" * 60)

    cli = RAGCLI()

    # Get repository URL from command line argument or user input
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        repo_url = input("Enter repository URL or path: ").strip()
        if not repo_url:
            logger.error("No repository URL provided. Exiting.")
            return

    # Index the repository
    success = await cli.index_repository(repo_url)
    if not success:
        logger.error("Failed to index repository. Exiting.")
        return

    # Start interactive mode
    await cli.interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
