"""
GitHub Repository Indexing and Q&A Tool

Main FastAPI application with RAG pipeline for indexing GitHub repositories
and providing Q&A capabilities about codebases.
"""

import logging
import uuid
from typing import Dict
from urllib.parse import urlparse
import asyncio
import aiohttp

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import constants
from models.schemas import IndexRequest, QueryRequest, QueryResponse, StatusResponse
from services.rag_service import RAGService
from services.repository_service import RepositoryService
from utils import (
    load_sessions,
    save_sessions,
    index_repository_background,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitHub Repository Indexing & Q&A Tool",
    description="A RAG-powered tool for indexing GitHub repositories and answering questions about codebases",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=constants.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
repository_service = RepositoryService()
rag_service = RAGService()

# Session storage file
SESSION_FILE = constants.SESSIONS_FILE


def validate_github_url(url: str) -> bool:
    """Validate if the URL is a valid GitHub repository URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if valid GitHub URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        
        # Check if it's HTTPS
        if parsed.scheme != 'https':
            return False
            
        # Check if it's from GitHub
        if parsed.netloc not in ['github.com', 'www.github.com']:
            return False
            
        # Check if it has the correct path format (username/repository)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            return False
            
        # Check if it's not a special GitHub page (like issues, pull requests, etc.)
        invalid_paths = ['issues', 'pulls', 'actions', 'projects', 'wiki', 'settings', 'security', 'insights']
        if any(part in invalid_paths for part in path_parts[2:]):
            return False
            
        return True
        
    except Exception:
        return False


async def check_repository_accessibility(url: str) -> tuple[bool, str]:
    """Check if a GitHub repository is accessible.
    
    Args:
        url: The GitHub repository URL to check
        
    Returns:
        tuple: (is_accessible, error_message)
    """
    try:
        # Convert to GitHub API URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            return False, "Invalid repository path"
            
        owner = path_parts[0]
        repo = path_parts[1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as response:
                if response.status == 200:
                    return True, ""
                elif response.status == 404:
                    return False, "Repository not found. It may be private or doesn't exist."
                elif response.status == 403:
                    return False, "Repository is private or access is forbidden."
                else:
                    return False, f"Repository is not accessible (HTTP {response.status})"
                    
    except asyncio.TimeoutError:
        return False, "Timeout while checking repository accessibility"
    except Exception as e:
        return False, f"Error checking repository: {str(e)}"




# Load existing sessions
session_status: Dict[str, Dict] = load_sessions(SESSION_FILE)


class IndexResponse(BaseModel):
    message: str
    session_id: str


@app.post("/index", response_model=IndexResponse)
async def index_repository(
    request: IndexRequest, background_tasks: BackgroundTasks
) -> IndexResponse:
    """Start indexing a GitHub repository.

    Args:
        request: IndexRequest containing the repository URL to index.
        background_tasks: FastAPI background tasks for async processing.

    Returns:
        IndexResponse with session_id for tracking indexing progress.

    Raises:
        HTTPException: If indexing fails to start.
    """
    try:
        # Validate the GitHub URL format
        if not validate_github_url(request.repo_url):
            raise HTTPException(
                status_code=400, 
                detail="Invalid URL. Please provide a valid GitHub repository URL (e.g., https://github.com/username/repository)"
            )
        
        # Check if the repository is accessible
        is_accessible, error_message = await check_repository_accessibility(request.repo_url)
        if not is_accessible:
            raise HTTPException(
                status_code=400,
                detail=error_message
            )
        
        session_id = str(uuid.uuid4())

        # Initialize session status
        session_status[session_id] = {
            "status": "indexing",
            "message": "Starting repository cloning...",
            "progress": 0,
        }
        save_sessions(session_status, SESSION_FILE)

        # Start background indexing task
        background_tasks.add_task(
            index_repository_background, 
            session_id, 
            str(request.repo_url),
            session_status,
            SESSION_FILE,
            repository_service,
            rag_service
        )

        return IndexResponse(
            message="Repository indexing started.", session_id=session_id
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Invalid request data: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}") from e
    except Exception as e:
        logger.error("Unexpected error starting indexing: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during indexing initialization",
        ) from e


@app.get("/status/{session_id}", response_model=StatusResponse)
async def get_indexing_status(session_id: str) -> StatusResponse:
    """Get the current status of repository indexing.

    Args:
        session_id: Unique identifier for the indexing session.

    Returns:
        StatusResponse containing current indexing status and progress.

    Raises:
        HTTPException: If session_id is not found.
    """
    if session_id not in session_status:
        raise HTTPException(status_code=404, detail="Session not found")

    return StatusResponse(**session_status[session_id])


@app.post("/query", response_model=QueryResponse)
async def query_repository(request: QueryRequest) -> QueryResponse:
    """Query the indexed repository using RAG pipeline.

    Args:
        request: QueryRequest containing session_id and question.

    Returns:
        QueryResponse with answer, sources, and confidence score.

    Raises:
        HTTPException: If session not found, repository not ready, or query fails.
    """
    try:
        if request.session_id not in session_status:
            raise HTTPException(status_code=404, detail="Session not found")

        session_data = session_status[request.session_id]

        if session_data["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Repository not ready for queries. Status: {session_data['status']}",
            )

        # Perform RAG query
        result = await rag_service.query(
            session_id=request.session_id, question=request.question
        )

        return QueryResponse(**result)

    except ValueError as e:
        logger.error("Invalid query request: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid query: {e}") from e
    except Exception as e:
        logger.error("Unexpected error processing query: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error during query processing"
        ) from e




if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=constants.HOST,
        port=constants.PORT,
        reload=True,
        log_level="info",
    )
