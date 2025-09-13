"""
Pydantic models for API request/response schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class IndexRequest(BaseModel):
    repo_url: str


class QueryRequest(BaseModel):
    session_id: str
    question: str


class StatusResponse(BaseModel):
    status: str  # "indexing", "ready", "error"
    message: str
    progress: Optional[int] = None


class Source(BaseModel):
    file: str
    snippet: str
    line_number: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: Optional[str] = None  # "high", "medium", "low"


class FileInfo(BaseModel):
    path: str
    content: str
    file_type: str
    size: int
