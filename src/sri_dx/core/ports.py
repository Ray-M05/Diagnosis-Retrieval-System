from abc import ABC, abstractmethod
from typing import List, Any
from .schemas import Document, Query, Evidence

class IndexStore(ABC):
    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        pass

    @abstractmethod
    def search(self, query: str) -> List[Document]:
        pass

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, ids: List[str], vectors: List[List[float]], metadata: List[dict]) -> None:
        pass

    @abstractmethod
    def query(self, vector: List[float], top_k: int = 5) -> List[dict]:
        pass

class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: Query) -> List[Evidence]:
        pass

class Ranker(ABC):
    @abstractmethod
    def rank(self, query: Query, candidates: List[Evidence]) -> List[Evidence]:
        pass
