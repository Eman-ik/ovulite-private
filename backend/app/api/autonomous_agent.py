"""
FastAPI Routes for Ovulite Autonomous Agent
Exposes all 4 phases through REST endpoints
"""

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Heavy imports moved inside functions to allow backend to start without all dependencies
# from app.autonomous_agent.phase1_semantic import SQLQueryEngine, SQLQueryRequest, SQLQueryResponse, VectorStoreManager
# from app.autonomous_agent.phase2_diagnostics import SHAPDiagnosticsEngine, DiagnosticReport
# from app.autonomous_agent.phase3_watchdog import ProactiveWatchdog, SystemNotification
# from app.autonomous_agent.phase4_research import ResearchIntegrator, ResearchInsight
from app.auth.dependencies import require_role
from app.database import DATABASE_URL, get_db

# Every route below reaches into the database directly (some execute
# near-raw SQL) and none of it is in the SRS's authorized surface, so the
# whole router is gated to admins rather than left open to any caller.
router = APIRouter(
    prefix="/api/autonomous-agent",
    tags=["autonomous_agent"],
    dependencies=[Depends(require_role("admin"))],
)


_DISALLOWED_SQL_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|attach|pragma|exec|call)\b",
    re.IGNORECASE,
)


def _ensure_read_only_query(sql: str) -> None:
    """Reject anything but a single read-only SELECT/CTE statement.

    There is no NL-to-SQL translation behind this endpoint (see
    phase1_semantic/text_to_sql.py) — the caller's string reaches the
    database close to verbatim, so it must never be allowed to write, alter
    or drop anything.
    """
    stripped = (sql or "").strip().rstrip(";")
    if not stripped:
        raise HTTPException(status_code=400, detail="Query must not be empty")
    if ";" in stripped:
        raise HTTPException(status_code=400, detail="Multiple statements are not allowed")
    if not re.match(r"^\s*(select|with)\b", stripped, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    if _DISALLOWED_SQL_KEYWORDS.search(stripped):
        raise HTTPException(status_code=400, detail="Query contains a disallowed keyword")


# ============================================================================
# Phase 1: Semantic Knowledge Layer
# ============================================================================

@router.post("/query")
async def query_knowledge_base(
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Run a read-only SQL query against the ET knowledge tables.

    Admin-only. This is not natural-language search — the caller supplies a
    SQL SELECT directly, so it is restricted to a single read-only statement.
    """
    from app.autonomous_agent.phase1_semantic import SQLQueryEngine, SQLQueryRequest

    query_text = (payload or {}).get("query", "")
    _ensure_read_only_query(query_text)

    try:
        engine = SQLQueryEngine(database_url=DATABASE_URL)
        request = SQLQueryRequest(query=query_text, context=(payload or {}).get("context"))
        response = await engine.query(request)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming-et-records")
async def get_upcoming_et_records(
    days_ahead: int = 7,
    db: Session = Depends(get_db)
):
    """Get all ET records scheduled for the next N days."""
    try:
        engine = SQLQueryEngine(
            database_url=DATABASE_URL
        )
        
        records = engine.get_upcoming_et_records()
        return {
            "count": len(records),
            "records": records,
            "days_ahead": days_ahead
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector-search")
async def search_knowledge_base(
    query: str,
    k: int = 5,
    threshold: float = 0.7
):
    """
    Search the knowledge base using keyword matching.
    
    Example: "embryo quality assessment techniques"
    Note: Uses keyword-based search (pgvector not required)
    """
    try:
        vector_store = VectorStoreManager(
            database_url=DATABASE_URL
        )
        
        results = await vector_store.search(query, k=k, threshold=threshold)
        
        return {
            "query": query,
            "results_count": len(results),
            "search_mode": "keyword_matching",
            "note": "Keyword-based search mode (pgvector not required)",
            "results": [
                {
                    "content": r.content,
                    "similarity_score": r.similarity_score,
                    "source": r.source,
                    "metadata": r.metadata
                }
                for r in results
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 2: Observability & Diagnostics Layer
# ============================================================================

@router.post("/diagnose/prediction")
async def diagnose_prediction(
    transfer_id: int,
    model_name: str,
    prediction_score: float,
    input_features: Optional[dict] = None
):
    """
    Generate a diagnostic report for a model prediction.
    
    Uses SHAP values to explain which features drove the prediction.
    """
    try:
        from app.autonomous_agent.phase2_diagnostics import SHAPDiagnosticsEngine
        diagnostics = SHAPDiagnosticsEngine()
        
        # For XGBoost models
        if "xgboost" in model_name.lower():
            import numpy as np
            
            # Convert input features to numpy array
            features_array = np.array([input_features.values()]) if input_features else np.random.randn(1, 10)
            feature_names = list(input_features.keys()) if input_features else [f"feature_{i}" for i in range(10)]
            
            report = diagnostics.explain_xgboost_prediction(
                features_array,
                feature_names,
                prediction_score
            )
            
            report.transfer_id = transfer_id
            
            return report
        
        else:
            raise ValueError(f"Model type not supported: {model_name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagnostics/low-confidence")
async def get_low_confidence_diagnostics(
    threshold: float = 0.85,
    limit: int = 10
):
    """Get diagnostic analysis for low-confidence predictions."""
    try:
        engine = SQLQueryEngine(
            database_url=DATABASE_URL
        )
        
        predictions = engine.get_low_confidence_predictions(threshold)
        
        return {
            "threshold": threshold,
            "count": len(predictions),
            "predictions": predictions[:limit]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 3: Proactive Watchdog Layer
# ============================================================================

@router.get("/watchdog/status")
async def get_watchdog_status():
    """Get status of the proactive watchdog monitoring."""
    try:
        from app.autonomous_agent.phase3_watchdog import ProactiveWatchdog
        watchdog = ProactiveWatchdog(
            database_url=DATABASE_URL
        )
        
        return {
            "status": "running" if watchdog.scheduler.running else "stopped",
            "check_interval_minutes": watchdog.check_interval_minutes,
            "confidence_threshold": watchdog.confidence_threshold,
            "et_warning_hours": watchdog.et_warning_hours,
            "active_triggers": len([t for t in watchdog.triggers if t.active])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchdog/start")
async def start_watchdog():
    """Start the proactive watchdog monitoring."""
    try:
        watchdog = ProactiveWatchdog(
            database_url=DATABASE_URL
        )
        
        watchdog.start_monitoring()
        
        return {
            "status": "started",
            "message": "Proactive watchdog is now monitoring system"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchdog/run-check")
async def run_manual_watchdog_check():
    """Manually trigger a watchdog health check."""
    try:
        watchdog = ProactiveWatchdog(
            database_url=DATABASE_URL
        )
        
        await watchdog.run_health_check()
        
        return {
            "status": "check_completed",
            "message": "Health check executed"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 4: Research Intelligence Layer
# ============================================================================

@router.post("/research/discover")
async def discover_research_insights(
    keywords: Optional[List[str]] = None,
    max_results: int = 20
):
    """
    Discover research papers from arXiv relevant to Ovulite.
    
    Analyzes papers for improvements to CNN and XGBoost models.
    """
    try:
        from app.autonomous_agent.phase4_research import ResearchIntegrator
        integrator = ResearchIntegrator()
        
        insights = await integrator.discover_and_integrate(keywords)
        
        # Sort by relevance
        insights_sorted = sorted(insights, key=lambda x: x.relevance_score, reverse=True)
        
        return {
            "count": len(insights_sorted),
            "insights": [
                {
                    "title": i.title,
                    "insight": i.insight,
                    "relevance_score": i.relevance_score,
                    "implementation_tip": i.implementation_tip,
                    "related_components": i.related_components,
                    "paper_url": i.paper_url
                }
                for i in insights_sorted[:max_results]
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/methods-profile")
async def get_ovulite_methods_profile():
    """Get the profile of Ovulite's current AI methods for research matching."""
    try:
        from app.autonomous_agent.phase4_research import OvuliteMethodProfile
        
        profile = OvuliteMethodProfile()
        
        return {
            "methods": {
                method: {
                    "description": details["description"],
                    "keywords": details["keywords"],
                    "improvement_areas": details["improvement_areas"]
                }
                for method, details in profile.methods.items()
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
