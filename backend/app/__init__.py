"""
Ovulite Autonomous Agent - Multi-Phase Implementation

Phase 1: Semantic Knowledge Layer (Data Awareness)
- Text-to-SQL bridge using LangChain
- Vector store (pgvector) for semantic search

Phase 2: Observability & Diagnostics Layer (The "Why")
- SHAP-based model explainability
- Feature importance analysis
- Confidence assessment and recommendations

Phase 3: Proactive Watchdog Layer (Automation)
- FastAPI Background Tasks
- APScheduler for monitoring
- Automated notifications and alerts

Phase 4: Research Intelligence Layer (External Growth)
- arXiv integration
- Paper relevance matching
- Implementation suggestions
"""

# from app.autonomous_agent.phase1_semantic import (
#     SQLQueryEngine,
#     VectorStoreManager,
#     SQLQueryRequest,
#     SQLQueryResponse,
#     DocumentChunk,
#     VectorSearchResult,
# )

# from app.autonomous_agent.phase2_diagnostics import (
#     SHAPDiagnosticsEngine,
#     DiagnosticReport,
#     DiagnosticFeature,
#     ModelMetadata,
# )

# from app.autonomous_agent.phase3_watchdog import (
#     ProactiveWatchdog,
#     SystemNotification,
#     WatchdogTrigger,
#     NotificationType,
# )

# from app.autonomous_agent.phase4_research import (
#     ResearchScout,
#     ResearchIntegrator,
#     ResearchInsight,
#     ResearchPaper,
#     OvuliteMethodProfile,
# )

__all__ = [
    # Phase 1
    "SQLQueryEngine",
    "VectorStoreManager",
    "SQLQueryRequest",
    "SQLQueryResponse",
    "DocumentChunk",
    "VectorSearchResult",
    # Phase 2
    "SHAPDiagnosticsEngine",
    "DiagnosticReport",
    "DiagnosticFeature",
    "ModelMetadata",
    # Phase 3
    "ProactiveWatchdog",
    "SystemNotification",
    "WatchdogTrigger",
    "NotificationType",
    # Phase 4
    "ResearchScout",
    "ResearchIntegrator",
    "ResearchInsight",
    "ResearchPaper",
    "OvuliteMethodProfile",
]
