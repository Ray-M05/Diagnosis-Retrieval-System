from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Document(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Evidence(BaseModel):
    doc_id: str
    snippet: str
    score: float
    source: Optional[str] = None

class Query(BaseModel):
    text: str
    filters: Dict[str, Any] = Field(default_factory=dict)

class SearchResult(BaseModel):
    query: Query
    results: List[Evidence]
    explanation: Optional[str] = None
