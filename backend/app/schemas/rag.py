from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=8, ge=1, le=20)


class RagDocOut(BaseModel):
    table_name: str
    column_name: str | None
    content: str
    similarity: float


class RagSearchResponse(BaseModel):
    question: str
    results: list[RagDocOut]
    prompt_context: str
