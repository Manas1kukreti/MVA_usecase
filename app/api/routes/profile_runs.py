"""Profile runs API routes."""

import uuid
import json
from typing import Any

from fastapi import APIRouter, Depends, UploadFile, File, Form

from app.core.config import Settings
from app.core.enums import RunStatus
from app.core.logging import get_logger
from app.api.dependencies import get_cached_settings
from app.api.auth import get_current_user
from app.repositories.configuration_repository import ConfigurationRepository
from app.services.ingestion.temporary_storage import TemporaryStorage
from app.services.llm.factory import create_llm_provider
from app.services.schema_intelligence.local_provider import LocalSchemaIntelligenceProvider
from app.services.orchestration.profiling_orchestrator import ProfilingOrchestrator
from app.services.orchestration.job_manager import JobManager, ExecutionMode
from app.schemas.requests import DrillDownRequest
from app.schemas.responses import RunCreatedResponse, FullResultResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/profile-runs", tags=["profile-runs"])

# In-memory result store for demo (production would use DB)
_results_store: dict[str, Any] = {}

# Job manager with background thread execution
_job_manager = JobManager(mode=ExecutionMode.BACKGROUND_THREAD)


def _get_orchestrator(settings: Settings) -> ProfilingOrchestrator:
    """Build orchestrator with current settings."""
    config_repo = ConfigurationRepository(config_dir="config")
    llm = create_llm_provider(settings)
    si = LocalSchemaIntelligenceProvider(llm)
    temp = TemporaryStorage(settings)
    return ProfilingOrchestrator(settings, config_repo, si, temp)


@router.post("", response_model=RunCreatedResponse)
async def create_profile_run(
    file: UploadFile = File(...),
    primary_domain: str = Form(...),
    schema_metadata: str = Form(default="{}"),
    request_rules: str = Form(default="[]"),
    settings: Settings = Depends(get_cached_settings),
    user: str = Depends(get_current_user),
) -> RunCreatedResponse:
    """
    Create and execute a profiling run.

    Accepts multipart/form-data with:
    - file: CSV or XLSX file
    - primary_domain: one of Payments, Customer, HR, Finance
    - schema_metadata: JSON string with column descriptions
    - request_rules: JSON string with additional rules
    """
    run_id = uuid.uuid4()

    # Parse JSON fields
    try:
        metadata = json.loads(schema_metadata) if schema_metadata else None
    except json.JSONDecodeError:
        metadata = None

    try:
        rules = json.loads(request_rules) if request_rules else None
    except json.JSONDecodeError:
        rules = None

    # Read file content
    content = await file.read()
    filename = file.filename or "upload"

    # Execute pipeline via job manager
    orchestrator = _get_orchestrator(settings)
    job = _job_manager.create_job(str(run_id))

    def _run_pipeline():
        return orchestrator.execute(
            run_id=run_id,
            file_content=content,
            filename=filename,
            primary_domain=primary_domain,
            schema_metadata=metadata,
            request_rules=rules,
        )

    _job_manager.submit(str(run_id), _run_pipeline)

    # Wait for completion (sync-like behavior for v1)
    completed_job = _job_manager.wait_for_completion(str(run_id), timeout=120.0)

    if completed_job and completed_job.result:
        result = completed_job.result
        _results_store[str(run_id)] = result

        if result.status == RunStatus.FAILED:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=422,
                content={"error": result.error},
            )

        return RunCreatedResponse(run_id=str(run_id), status=result.status.value)

    # Job still processing or failed at job level
    if completed_job and completed_job.error:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": completed_job.error})

    return RunCreatedResponse(run_id=str(run_id), status="processing")


@router.get("/{run_id}")
def get_run_summary(run_id: str) -> dict[str, Any]:
    """Get profile run summary."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)

    return {
        "run_id": result.run_id,
        "status": result.status.value,
        "primary_domain": result.primary_domain,
        "secondary_domain": result.secondary_domain,
        "dataset_profile": result.dataset_profile,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
    }


@router.get("/{run_id}/result")
def get_full_result(run_id: str) -> dict[str, Any]:
    """Get complete profiling result."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)

    return result.__dict__


@router.get("/{run_id}/columns")
def get_columns(run_id: str) -> dict[str, Any]:
    """Get column profiles."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)
    return {"columns": result.column_profiles}


@router.get("/{run_id}/quality")
def get_quality(run_id: str) -> dict[str, Any]:
    """Get quality assessments."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)
    return {"assessments": result.quality_assessments, "overall": result.overall_quality}


@router.get("/{run_id}/readiness")
def get_readiness(run_id: str) -> dict[str, Any]:
    """Get readiness assessments."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)
    return {"assessments": result.readiness_assessments}


@router.get("/{run_id}/hierarchy")
def get_hierarchy(run_id: str) -> dict[str, Any]:
    """Get hierarchy chain."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)
    return {"hierarchy": result.hierarchy}


@router.get("/{run_id}/charts")
def get_charts(run_id: str) -> dict[str, Any]:
    """Get chart specifications."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)
    return {"charts": result.charts}


@router.post("/{run_id}/charts/{chart_id}/drill-down")
def drill_down(run_id: str, chart_id: str, body: DrillDownRequest) -> dict[str, Any]:
    """Execute a drill-down request."""
    result = _results_store.get(run_id)
    if not result:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(run_id)

    from app.services.charts.drilldown_service import DrillDownService
    service = DrillDownService()
    hierarchy_levels = result.hierarchy.get("level_columns", [])

    return service.execute_drill_down(
        cubes=[],  # Would come from DB in production
        chart_id=chart_id,
        hierarchy_levels=hierarchy_levels,
        selected_path=body.selected_path,
    )
