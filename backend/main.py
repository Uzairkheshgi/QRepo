"""
GitHub Repository Indexing and Q&A Tool

Main FastAPI application with RAG pipeline for indexing GitHub repositories
and providing Q&A capabilities about codebases.
"""

import logging
import uuid
from typing import Dict

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
