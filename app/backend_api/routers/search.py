from fastapi import APIRouter, Query, HTTPException
from app.backend_api.services.retrieval import search_documents

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    size: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """
    BM25 full-text search over indexed documents.

    - Searches across title (weighted 3x) and content fields
    - Returns ranked results with highlighted snippets
    - Supports minor typo tolerance via fuzziness

    Args:
        q:    Search query string (required)
        size: Number of results to return (default: 10, max: 100)

    Returns:
        JSON with query, total match count, and ranked results
    """
    try:
        results = search_documents(query=q, size=size)
        return results

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )