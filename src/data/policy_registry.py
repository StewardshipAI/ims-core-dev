"""
IMS Policy Enforcement Engine - Data Layer
Policy Registry for CRUD operations on policies and violations.

This module handles all database interactions for:
- Policy definitions (create, read, update, delete)
- Policy violations (logging, querying, resolution)
- Policy executions (performance tracking)
- Compliance reporting
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql, errors

logger = logging.getLogger("ims.policy_registry")

class PolicyRegistryError(Exception):
    """Base exception for PolicyRegistry errors."""
    pass

class PolicyRegistry:
    """
    Data access layer for policy enforcement engine.
    
    Handles:
    - Policy CRUD operations
    - Violation logging and querying
    - Execution tracking
    - Compliance reporting
    """
    
    def __init__(self, db_connection_string: str):
        """
        Initialize PolicyRegistry with database connection.
        
        Args:
            db_connection_string: PostgreSQL connection string
        """
        self.conn_str = db_connection_string
        logger.info("PolicyRegistry initialized")
    
    def _get_connection(self):
        """Get database connection."""
        try:
            conn = psycopg2.connect(self.conn_str, cursor_factory=RealDictCursor)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
    
    # =========================================================================
    # POLICY CRUD OPERATIONS
    # =========================================================================
    
    async def get_active_policies(
        self, 
        evaluation_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch active policies.
        
        Args:
            evaluation_type: Filter by when policy is evaluated (pre_flight, etc.)
            category: Filter by category (cost, vendor, etc.)
        
        Returns:
            List of policy dicts
        """
        query = """
            SELECT 
                policy_id, name, category, enabled, priority,
                constraints, evaluation_type, action_on_violation,
                description, tags, created_at, updated_at
            FROM policies
            WHERE enabled = TRUE AND deleted_at IS NULL
        """
        params = []
        
        if evaluation_type:
            query += " AND evaluation_type = %s"
            params.append(evaluation_type)
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        query += " ORDER BY priority DESC, created_at ASC"
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    policies = cur.fetchall()
                    
                    # Convert RealDictRow to dict
                    return [dict(p) for p in policies]
                    
        except psycopg2.Error as e:
            logger.error(f"Error fetching policies: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    async def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get single policy by ID."""
        query = """
            SELECT *
            FROM policies
            WHERE policy_id = %s AND deleted_at IS NULL
        """
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, (policy_id,))
                    policy = cur.fetchone()
                    
                    return dict(policy) if policy else None
                    
        except psycopg2.Error as e:
            logger.error(f"Error fetching policy {policy_id}: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    async def create_policy(self, policy_data: Dict[str, Any]) -> str:
        """
        Create a new policy.
        
        Args:
            policy_data: Policy definition
        
        Returns:
            policy_id of created policy
        """
        query = """
            INSERT INTO policies (
                name, category, enabled, priority, constraints,
                evaluation_type, action_on_violation, description, tags, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING policy_id
        """
        
        params = (
            policy_data["name"],
            policy_data["category"],
            policy_data.get("enabled", True),
            policy_data.get("priority", 50),
            json.dumps(policy_data["constraints"]),
            policy_data["evaluation_type"],
            policy_data.get("action_on_violation", "warn"),
            policy_data.get("description"),
            policy_data.get("tags", []),
            policy_data.get("created_by", "system")
        )
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    conn.commit()
                    
                    policy_id = str(result["policy_id"])
                    logger.info(f"Created policy: {policy_id} ({policy_data['name']})")
                    return policy_id
                    
        except errors.UniqueViolation:
            conn.rollback()
            raise PolicyRegistryError(f"Policy with name '{policy_data['name']}' already exists")
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error creating policy: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    async def update_policy(
        self, 
        policy_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update policy fields.
        
        Args:
            policy_id: Policy to update
            updates: Fields to update
        
        Returns:
            True if updated, False if not found
        """
        # Allowed fields to update
        allowed_fields = {
            "enabled", "priority", "constraints", "action_on_violation",
            "description", "tags"
        }
        
        # Filter to allowed fields only
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build SET clause
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key == "constraints":
                # JSON field needs special handling
                set_clauses.append(sql.SQL("{} = %s::jsonb").format(sql.Identifier(key)))
                params.append(json.dumps(value))
            else:
                set_clauses.append(sql.SQL("{} = %s").format(sql.Identifier(key)))
                params.append(value)
        
        params.append(policy_id)
        
        query = sql.SQL("UPDATE policies SET {} WHERE policy_id = %s").format(
            sql.SQL(", ").join(set_clauses)
        )
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    rows_affected = cur.rowcount
                    conn.commit()
                    
                    if rows_affected > 0:
                        logger.info(f"Updated policy {policy_id}")
                    
                    return rows_affected > 0
                    
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error updating policy {policy_id}: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    async def delete_policy(self, policy_id: str) -> bool:
        """
        Soft delete a policy.
        
        Args:
            policy_id: Policy to delete
        
        Returns:
            True if deleted, False if not found
        """
        query = """
            UPDATE policies
            SET deleted_at = CURRENT_TIMESTAMP, enabled = FALSE
            WHERE policy_id = %s AND deleted_at IS NULL
        """
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, (policy_id,))
                    rows_affected = cur.rowcount
                    conn.commit()
                    
                    if rows_affected > 0:
                        logger.info(f"Deleted policy {policy_id}")
                    
                    return rows_affected > 0
                    
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error deleting policy {policy_id}: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    # =========================================================================
    # VIOLATION LOGGING & QUERYING
    # =========================================================================
    
    async def log_violation(self, violation) -> str:
        """
        Log a policy violation to the database.
        
        Args:
            violation: PolicyViolation instance
        
        Returns:
            violation_id
        """
        query = """
            INSERT INTO policy_violations (
                policy_id, correlation_id, violation_type, severity,
                violation_details, action_taken, detected_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING violation_id
        """
        
        params = (
            violation.policy_id,
            violation.correlation_id,
            violation.details.get("violation", "unknown"),
            violation.severity.value,
            json.dumps(violation.details),
            violation.action.value,
            violation.timestamp
        )
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    conn.commit()
                    
                    violation_id = str(result["violation_id"])
                    logger.info(
                        f"Logged violation: {violation_id} "
                        f"(policy={violation.policy_name}, "
                        f"action={violation.action.value})"
                    )
                    return violation_id
                    
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error logging violation: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    async def get_violations(
        self,
        policy_id: Optional[str] = None,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query policy violations with filters.
        
        Args:
            policy_id: Filter by specific policy
            severity: Filter by severity level
            resolved: Filter by resolution status
            start_date: Filter by date range (start)
            end_date: Filter by date range (end)
            limit: Maximum results (default 100, max 1000)
        
        Returns:
            List of violation dicts
        """
        query = """
            SELECT 
                pv.violation_id, pv.policy_id, p.name as policy_name,
                pv.correlation_id, pv.violation_type, pv.severity,
                pv.violation_details, pv.action_taken, pv.detected_at,
                pv.resolved, pv.resolved_at, pv.resolved_by, pv.resolution_notes
            FROM policy_violations pv
            LEFT JOIN policies p ON pv.policy_id = p.policy_id
            WHERE 1=1
        """
        params = []
        
        if policy_id:
            query += " AND pv.policy_id = %s"
            params.append(policy_id)
        
        if severity:
            query += " AND pv.severity = %s"
            params.append(severity)
        
        if resolved is not None:
            query += " AND pv.resolved = %s"
            params.append(resolved)
        
        if start_date:
            query += " AND pv.detected_at >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND pv.detected_at <= %s"
            params.append(end_date)
        
        query += " ORDER BY pv.detected_at DESC"
        query += f" LIMIT {min(limit, 1000)}"
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    violations = cur.fetchall()
                    
                    return [dict(v) for v in violations]
                    
        except psycopg2.Error as e:
            logger.error(f"Error fetching violations: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    async def resolve_violation(
        self, 
        violation_id: str, 
        resolution_notes: str,
        resolved_by: str = "system"
    ) -> bool:
        """
        Mark a violation as resolved.
        
        Args:
            violation_id: Violation to resolve
            resolution_notes: Notes about resolution
            resolved_by: Who resolved it
        
        Returns:
            True if updated, False if not found
        """
        query = """
            UPDATE policy_violations
            SET 
                resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by = %s,
                resolution_notes = %s
            WHERE violation_id = %s AND resolved = FALSE
        """
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, (resolved_by, resolution_notes, violation_id))
                    rows_affected = cur.rowcount
                    conn.commit()
                    
                    if rows_affected > 0:
                        logger.info(f"Resolved violation {violation_id}")
                    
                    return rows_affected > 0
                    
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error resolving violation {violation_id}: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    # =========================================================================
    # EXECUTION TRACKING
    # =========================================================================
    
    async def log_execution(
        self,
        policy_id: str,
        correlation_id: str,
        passed: bool,
        evaluation_time_ms: int,
        evaluation_input: Dict[str, Any],
        evaluation_output: Dict[str, Any]
    ) -> str:
        """
        Log a policy execution for analytics.
        
        Args:
            policy_id: Policy that was evaluated
            correlation_id: Request correlation ID
            passed: Whether policy check passed
            evaluation_time_ms: Time taken (milliseconds)
            evaluation_input: Input context
            evaluation_output: Evaluation result
        
        Returns:
            execution_id
        """
        query = """
            INSERT INTO policy_executions (
                policy_id, correlation_id, passed, evaluation_time_ms,
                evaluation_input, evaluation_output, evaluated_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, CURRENT_TIMESTAMP)
            RETURNING execution_id
        """
        
        params = (
            policy_id,
            correlation_id,
            passed,
            evaluation_time_ms,
            json.dumps(evaluation_input),
            json.dumps(evaluation_output)
        )
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    conn.commit()
                    
                    return str(result["execution_id"])
                    
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error logging execution: {e}")
            # Don't raise - logging failures shouldn't break the request
            return ""
        finally:
            conn.close()
    
    # =========================================================================
    # COMPLIANCE REPORTING
    # =========================================================================
    
    async def get_compliance_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get compliance statistics for reporting.
        
        Args:
            start_date: Report start date (default: 30 days ago)
            end_date: Report end date (default: now)
        
        Returns:
            Dict with compliance metrics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Query 1: Violation counts by severity
        query_violations = """
            SELECT 
                severity,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE resolved = TRUE) as resolved_count
            FROM policy_violations
            WHERE detected_at BETWEEN %s AND %s
            GROUP BY severity
        """
        
        # Query 2: Most violated policies
        query_top_violated = """
            SELECT 
                p.name,
                p.category,
                COUNT(pv.violation_id) as violation_count
            FROM policy_violations pv
            JOIN policies p ON pv.policy_id = p.policy_id
            WHERE pv.detected_at BETWEEN %s AND %s
            GROUP BY p.name, p.category
            ORDER BY violation_count DESC
            LIMIT 10
        """
        
        # Query 3: Daily trends
        query_daily = """
            SELECT 
                DATE(detected_at) as date,
                COUNT(*) as violations,
                COUNT(*) FILTER (WHERE action_taken = 'blocked') as blocked
            FROM policy_violations
            WHERE detected_at BETWEEN %s AND %s
            GROUP BY DATE(detected_at)
            ORDER BY date DESC
        """
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # Fetch violation counts
                    cur.execute(query_violations, (start_date, end_date))
                    violations_by_severity = [dict(row) for row in cur.fetchall()]
                    
                    # Fetch top violated policies
                    cur.execute(query_top_violated, (start_date, end_date))
                    top_violated = [dict(row) for row in cur.fetchall()]
                    
                    # Fetch daily trends
                    cur.execute(query_daily, (start_date, end_date))
                    daily_trends = [dict(row) for row in cur.fetchall()]
                    
                    return {
                        "period": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat()
                        },
                        "violations_by_severity": violations_by_severity,
                        "top_violated_policies": top_violated,
                        "daily_trends": daily_trends
                    }
                    
        except psycopg2.Error as e:
            logger.error(f"Error fetching compliance stats: {e}")
            raise PolicyRegistryError(f"Database error: {e}")
        finally:
            conn.close()
    
    # =========================================================================
    # MODEL METADATA (for cost calculations)
    # =========================================================================
    
    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch model metadata from model registry.
        
        This is a convenience method that queries the models table.
        Used by cost policy evaluator.
        
        Args:
            model_id: Model to fetch
        
        Returns:
            Model dict or None
        """
        query = """
            SELECT 
                model_id, vendor_id, cost_in_per_mil, cost_out_per_mil,
                context_window, capability_tier
            FROM models
            WHERE model_id = %s AND is_active = TRUE
        """
        
        conn = self._get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, (model_id,))
                    model = cur.fetchone()
                    
                    if model:
                        return dict(model)
                    return None
                    
        except psycopg2.Error as e:
            logger.error(f"Error fetching model {model_id}: {e}")
            # Return None instead of raising - this is optional metadata
            return None
        finally:
            conn.close()
