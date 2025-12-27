from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, HTTPException
from src.core.pcr import RecommendationService, RecommendationRequest
from src.core.events import EventPublisher, get_event_publisher, CloudEvent
from src.data.model_registry import ModelProfile, ModelRegistry
from src.api.model_registry_api import verify_admin, registry # Re-use registry singleton

router = APIRouter(prefix="/api/v1/recommend", tags=["PCR"])

# Dependency for Service
def get_pcr_service():
    return RecommendationService(registry)

@router.post(
    "",
    response_model=List[ModelProfile],
    summary="Get model recommendations"
)
async def recommend_models(
    request: Request,
    criteria: RecommendationRequest,
    service: RecommendationService = Depends(get_pcr_service),
    publisher: EventPublisher = Depends(get_event_publisher),
    _: str = Depends(verify_admin) # Secure for now
):
    """
    Get optimal model recommendations based on constraints.
    """
    try:
        results = service.recommend(criteria)
        
        # Emit Event
        await publisher.publish(CloudEvent(
            source="/api/v1/recommend",
            type="pcr.recommendation_generated",
            correlation_id=request.headers.get("X-Request-ID", str(uuid4())),
            data={
                "criteria": criteria.model_dump(),
                "match_count": len(results),
                "top_match": results[0].model_id if results else None
            }
        ))
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
