# src/core/policy_verifier.py

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

logger = logging.getLogger("ims.pve")

# =============================================================================
# ENUMS & DATA STRUCTURES
# =============================================================================

class PolicyCategory(Enum):
    """Policy classification categories."""
    COST = "cost"
    PERFORMANCE = "performance"
    VENDOR = "vendor"
    DATA_RESIDENCY = "data_residency"
    BEHAVIORAL = "behavioral"
    COMPLIANCE = "compliance"

class EvaluationType(Enum):
    """When policy should be evaluated."""
    PRE_FLIGHT = "pre_flight"        # Before request execution
    RUNTIME = "runtime"              # During execution
    POST_EXECUTION = "post_execution"  # After response received
    CONTINUOUS = "continuous"        # Background monitoring

class PolicyAction(Enum):
    """Actions to take on policy violation."""
    BLOCK = "block"      # Prevent execution
    WARN = "warn"        # Allow but warn
    LOG = "log"         # Record only
    DEGRADE = "degrade"   # Fallback to alternative

class ViolationSeverity(Enum):
    """Severity levels for violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class PolicyViolation:
    """Represents a policy violation."""
    policy_id: str
    policy_name: str
    category: PolicyCategory
    severity: ViolationSeverity
    details: Dict[str, Any]
    action: PolicyAction
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "action": self.action.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    passed: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_time_ms: int = 0
    policies_evaluated: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
            "evaluation_time_ms": self.evaluation_time_ms,
            "policies_evaluated": self.policies_evaluated
        }

@dataclass
class EvaluationContext:
    """Context information for policy evaluation."""
    # Request Details
    model_id: str
    vendor_id: str
    estimated_tokens: int
    prompt: str
    
    # User Context
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Optional Metadata
    system_instruction: Optional[str] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    
    # Execution Context
    timestamp: datetime = field(default_factory=datetime.utcnow)
    environment: str = "production"  # production, staging, development
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "vendor_id": self.vendor_id,
            "estimated_tokens": self.estimated_tokens,
            "prompt_length": len(self.prompt),
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "environment": self.environment
        }

# =============================================================================
# POLICY VERIFIER ENGINE
# =============================================================================

class PolicyVerifierEngine:
    """
    Core policy evaluation engine.
    
    Evaluates requests against defined policies and determines:
    - Whether to allow execution
    - What warnings to surface
    - What fallback actions to take
    """
    
    def __init__(self, registry, event_publisher, model_registry=None):
        """
        Initialize the Policy Verifier Engine.
        """
        self.registry = registry
        self.publisher = event_publisher
        self.model_registry = model_registry
        
        # Register category-specific evaluators
        self.evaluators = {
            PolicyCategory.COST: self._evaluate_cost_policy,
            PolicyCategory.PERFORMANCE: self._evaluate_performance_policy,
            PolicyCategory.VENDOR: self._evaluate_vendor_policy,
            PolicyCategory.BEHAVIORAL: self._evaluate_behavioral_policy,
            PolicyCategory.DATA_RESIDENCY: self._evaluate_data_residency_policy,
            PolicyCategory.COMPLIANCE: self._evaluate_compliance_policy,
        }
        
        logger.info("PolicyVerifierEngine initialized (No Censorship Mode)")
    
    async def evaluate_pre_flight(
        self, 
        context: EvaluationContext
    ) -> PolicyResult:
        """
        Evaluate policies BEFORE executing a request.
        """
        start_time = datetime.utcnow()
        
        try:
            # Fetch active pre-flight policies
            policies = await self.registry.get_active_policies(
                evaluation_type=EvaluationType.PRE_FLIGHT.value
            )
            
            violations = []
            warnings = []
            policies_evaluated = 0
            
            for policy in policies:
                try:
                    result = await self._evaluate_policy(policy, context)
                    policies_evaluated += 1
                    
                    if not result["passed"]:
                        # Create violation record
                        violation = PolicyViolation(
                            policy_id=str(policy["policy_id"]),
                            policy_name=policy["name"],
                            category=PolicyCategory(policy["category"]),
                            severity=self._determine_severity(policy),
                            details=result["details"],
                            action=self._determine_action(policy, result),
                            correlation_id=context.correlation_id
                        )
                        violations.append(violation)
                        
                        # Log violation to database
                        await self.registry.log_violation(violation)
                        
                        # Emit telemetry event
                        await self._emit_violation_event(violation)
                    
                    if result.get("warnings"):
                        warnings.extend(result["warnings"])
                        
                except Exception as e:
                    logger.error(f"Error evaluating policy {policy.get('policy_id')}: {e}")
                    warnings.append({
                        "policy": policy.get("name", "unknown"),
                        "error": str(e),
                        "message": "Policy evaluation failed"
                    })
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return PolicyResult(
                passed=len(violations) == 0,
                violations=violations,
                warnings=warnings,
                evaluation_time_ms=duration_ms,
                policies_evaluated=policies_evaluated
            )
            
        except Exception as e:
            logger.error(f"Pre-flight evaluation failed: {e}")
            raise
    
    async def _evaluate_policy(self, policy, context) -> Dict[str, Any]:
        """Dispatch to category-specific evaluator."""
        try:
            category = PolicyCategory(policy["category"])
            evaluator = self.evaluators.get(category)
            if not evaluator:
                return {"passed": True, "details": {}, "warnings": []}
            return await evaluator(policy, context)
        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            return {"passed": True, "details": {"error": str(e)}, "warnings": []}
    
    async def _evaluate_cost_policy(self, policy, context) -> Dict[str, Any]:
        """Evaluate cost constraints."""
        constraints = policy["constraints"]
        details = {}
        warnings = []
        
        if self.model_registry:
            try:
                # model_registry methods are sync in this project's implementation usually, 
                # but let's check. Actually model_registry.get_model is sync.
                # Wait, I updated it to be async in one of my previous turns? No, let's check.
                # Based on src/data/model_registry.py it's sync.
                model = self.model_registry.get_model(context.model_id)
                if not model:
                    warnings.append({"message": f"Model {context.model_id} not found"})
                    avg_cost_per_mil = 1.0
                else:
                    avg_cost_per_mil = (float(model.cost_in_per_mil) + float(model.cost_out_per_mil)) / 2
            except Exception as e:
                avg_cost_per_mil = 1.0
        else:
            avg_cost_per_mil = 1.0
        
        estimated_cost = (float(context.estimated_tokens) / 1_000_000) * avg_cost_per_mil
        details["estimated_cost"] = round(estimated_cost, 6)
        
        if "max_cost_per_request" in constraints:
            max_cost = float(constraints["max_cost_per_request"])
            if estimated_cost > max_cost:
                details["violation"] = "cost_per_request_exceeded"
                details["limit"] = max_cost
                return {"passed": False, "details": details, "warnings": warnings}
        
        if "max_daily_cost" in constraints:
            daily_cost = await self._get_daily_cost(context.user_id)
            if daily_cost + estimated_cost > float(constraints["max_daily_cost"]):
                details["violation"] = "daily_budget_exceeded"
                details["limit"] = constraints["max_daily_cost"]
                return {"passed": False, "details": details, "warnings": warnings}
        
        return {"passed": True, "details": details, "warnings": warnings}
    
    async def _evaluate_vendor_policy(self, policy, context) -> Dict[str, Any]:
        """Evaluate vendor restriction policies."""
        constraints = policy["constraints"]
        details = {"vendor": context.vendor_id}
        
        if "allowed_vendors" in constraints:
            allowed = [v.lower() for v in constraints["allowed_vendors"]]
            if context.vendor_id.lower() not in allowed:
                details["violation"] = "vendor_not_allowed"
                return {"passed": False, "details": details, "warnings": []}
        
        if "blocked_vendors" in constraints:
            blocked = [v.lower() for v in constraints["blocked_vendors"]]
            if context.vendor_id.lower() in blocked:
                details["violation"] = "vendor_blocked"
                return {"passed": False, "details": details, "warnings": []}
        
        return {"passed": True, "details": details, "warnings": []}
    
    async def _evaluate_behavioral_policy(self, policy, context) -> Dict[str, Any]:
        """Evaluate technical behavioral limits (No keyword policing)."""
        constraints = policy["constraints"]
        details = {}
        
        if "max_prompt_length" in constraints:
            max_length = int(constraints["max_prompt_length"])
            prompt_length = len(context.prompt)
            if prompt_length > max_length:
                details["violation"] = "prompt_too_long"
                details["limit"] = max_length
                return {"passed": False, "details": details, "warnings": []}
        
        return {"passed": True, "details": details, "warnings": []}
    
    async def _evaluate_performance_policy(self, policy, context) -> Dict[str, Any]:
        """Evaluate performance SLA (stub)."""
        return {"passed": True, "details": {}, "warnings": []}
    
    async def _evaluate_data_residency_policy(self, policy, context) -> Dict[str, Any]:
        """Evaluate data residency (stub)."""
        return {"passed": True, "details": {}, "warnings": []}
    
    async def _evaluate_compliance_policy(self, policy, context) -> Dict[str, Any]:
        """Evaluate compliance/audit (stub)."""
        return {"passed": True, "details": {}, "warnings": []}
    
    def _determine_severity(self, policy) -> ViolationSeverity:
        priority = policy.get("priority", 50)
        if priority >= 90: return ViolationSeverity.CRITICAL
        elif priority >= 70: return ViolationSeverity.HIGH
        elif priority >= 40: return ViolationSeverity.MEDIUM
        else: return ViolationSeverity.LOW
    
    def _determine_action(self, policy, result) -> PolicyAction:
        if "action_on_violation" in policy:
            try:
                return PolicyAction(policy["action_on_violation"])
            except: pass
        severity = self._determine_severity(policy)
        if severity == ViolationSeverity.CRITICAL: return PolicyAction.BLOCK
        if severity == ViolationSeverity.HIGH and policy["category"] == "cost": return PolicyAction.DEGRADE
        return PolicyAction.BLOCK if severity == ViolationSeverity.HIGH else PolicyAction.WARN
    
    async def _emit_violation_event(self, violation: PolicyViolation):
        try:
            from src.schemas.events import CloudEvent
            event = CloudEvent(
                source="/policy/verifier",
                type="policy.violation.detected",
                correlation_id=violation.correlation_id,
                data=violation.to_dict()
            )
            await self.publisher.publish(event)
        except Exception as e:
            logger.error(f"Failed to emit violation event: {e}")
    
    async def _get_daily_cost(self, user_id: Optional[str]) -> float:
        return 0.0 # Stub