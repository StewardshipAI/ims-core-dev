"""
IMS Policy Enforcement Engine - Compliance API Router
FastAPI endpoints for compliance reporting and policy management.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from src.api.auth_utils import verify_admin
from src.data.policy_registry import PolicyRegistry
import os

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])

# Dependency injection
def get_policy_registry():
    """Get PolicyRegistry instance."""
    db_conn = os.getenv("DB_CONNECTION_STRING")
    return PolicyRegistry(db_conn)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ViolationReport(BaseModel):
    """Policy violation report."""
    violation_id: str
    policy_id: str
    policy_name: str
    correlation_id: Optional[str]
    violation_type: str
    severity: str
    action_taken: str
    detected_at: datetime
    resolved: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "violation_id": "123e4567-e89b-12d3-a456-426614174000",
                "policy_id": "456e4567-e89b-12d3-a456-426614174000",
                "policy_name": "free-tier-daily-budget",
                "correlation_id": "req-789",
                "violation_type": "daily_budget_exceeded",
                "severity": "critical",
                "action_taken": "blocked",
                "detected_at": "2025-12-31T10:30:00Z",
                "resolved": False
            }
        }

class ComplianceStats(BaseModel):
    """Compliance statistics."""
    period: dict
    violations_by_severity: List[dict]
    top_violated_policies: List[dict]
    daily_trends: List[dict]

class ViolationResolution(BaseModel):
    """Violation resolution data."""
    notes: str = Field(..., min_length=10, max_length=1000)
    resolved_by: str = Field(default="admin")

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/violations", response_model=List[ViolationReport])
async def get_violations(
    policy_id: Optional[str] = Query(None, description="Filter by policy ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    start_date: Optional[datetime] = Query(None, description="Filter start date"),
    end_date: Optional[datetime] = Query(None, description="Filter end date"),
    limit: int = Query(100, le=1000, description="Maximum results"),
    _: str = Depends(verify_admin),
    registry: PolicyRegistry = Depends(get_policy_registry)
):
    """
    Retrieve policy violation history.
    
    **Requires Admin API Key**
    
    Query filters:
    - policy_id: Specific policy
    - severity: low, medium, high, critical
    - resolved: true/false
    - start_date: ISO 8601 format
    - end_date: ISO 8601 format
    - limit: Max 1000 results
    """
    try:
        violations = await registry.get_violations(
            policy_id=policy_id,
            severity=severity,
            resolved=resolved,
            start_date=start_date or datetime.utcnow() - timedelta(days=30),
            end_date=end_date or datetime.utcnow(),
            limit=limit
        )
        return violations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch violations: {str(e)}"
        )

@router.get("/statistics", response_model=ComplianceStats)
async def get_compliance_statistics(
    start_date: Optional[datetime] = Query(None, description="Report start date"),
    end_date: Optional[datetime] = Query(None, description="Report end date"),
    _: str = Depends(verify_admin),
    registry: PolicyRegistry = Depends(get_policy_registry)
):
    """
    Get compliance statistics and trends.
    
    **Requires Admin API Key**
    
    Returns:
    - Violations by severity
    - Most violated policies
    - Daily violation trends
    - Resolution rates
    """
    try:
        stats = await registry.get_compliance_stats(
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )

@router.patch("/violations/{violation_id}/resolve")
async def resolve_violation(
    violation_id: str,
    resolution: ViolationResolution,
    _: str = Depends(verify_admin),
    registry: PolicyRegistry = Depends(get_policy_registry)
):
    """
    Mark a violation as resolved.
    
    **Requires Admin API Key**
    
    Request body:
    ```json
    {
        "notes": "Resolved by increasing user's daily budget limit",
        "resolved_by": "admin@example.com"
    }
    ```
    """
    try:
        success = await registry.resolve_violation(
            violation_id=violation_id,
            resolution_notes=resolution.notes,
            resolved_by=resolution.resolved_by
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Violation {violation_id} not found or already resolved"
            )
        
        return {
            "status": "resolved",
            "violation_id": violation_id,
            "resolved_by": resolution.resolved_by
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve violation: {str(e)}"
        )

@router.get("/policies", response_model=List[dict])
async def list_active_policies(
    category: Optional[str] = Query(None, description="Filter by category"),
    _: str = Depends(verify_admin),
    registry: PolicyRegistry = Depends(get_policy_registry)
):
    """
    List all active policies.
    
    **Requires Admin API Key**
    """
    try:
        policies = await registry.get_active_policies(category=category)
        return policies
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch policies: {str(e)}"
        )
