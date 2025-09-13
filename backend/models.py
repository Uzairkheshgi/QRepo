from typing import List, Optional

from pydantic import BaseModel


class FileInfo(BaseModel):
    """Information about a file in the repository"""

    path: str
    content: str
    file_type: str


class Source(BaseModel):
    """Source information for an answer"""

    file: str
    snippet: str
    line_number: Optional[int] = None


class QueryResponse(BaseModel):
    """Response to a query about the repository"""

    answer: str
    sources: List[Source]
    confidence: str
