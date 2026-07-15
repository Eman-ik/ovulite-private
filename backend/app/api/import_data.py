"""Production data-intake endpoints with validation and quarantine gates."""

from __future__ import annotations

import csv
import json
import logging
import shutil
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.user import User
from app.services.data_intake import DATA_ROOT, DataIntakeService

logger = logging.getLogger(__name__)
router = APIRouter()
intake_service = DataIntakeService()


def _ingest_clean_csv(result, db: Session, current_user: User) -> dict:
    if result.clean_csv_path is None or result.summary.get("accepted_rows", 0) == 0:
        return {"rows_read": 0, "rows_ingested": 0, "rows_skipped": 0, "errors": []}
    scripts_dir = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from ingest_et_data import ingest_et_data

    try:
        stats = ingest_et_data(
            str(result.clean_csv_path), db,
            organization_id=current_user.organization_id, commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Validated CSV failed during database ingestion")
        raise HTTPException(status_code=500, detail="Validated file could not be committed to the clinical database")
    return stats


async def _process_upload(file: UploadFile, db: Session, current_user: User, csv_only: bool = False) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Upload must include a filename")
    suffix = Path(file.filename).suffix.lower()
    allowed = {".csv"} if csv_only else {".csv", ".zip"}
    if suffix not in allowed:
        label = "CSV" if csv_only else "CSV or ZIP"
        raise HTTPException(status_code=400, detail=f"Only {label} files are accepted")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 250 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Upload exceeds the 250 MB intake limit")

    result = intake_service.process(file.filename, content, uploaded_by=current_user.username)
    response = result.response()
    response.update({"message": "File quarantined" if result.quarantined else "Validation complete"})
    if result.quarantined:
        return response
    if result.metadata["file_type"] == "csv":
        stats = _ingest_clean_csv(result, db, current_user)
        response.update(stats)
        response["message"] = "CSV validated and imported"
        project_root = Path(__file__).resolve().parents[3]
        for target in (
            project_root / "frontend" / "public" / "datasets" / "ET Summary - ET Data.csv",
            project_root / "docs" / "dataset" / "ET Summary - ET Data.csv",
        ):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(result.clean_csv_path, target)
    return response


@router.post("/file", status_code=status.HTTP_200_OK, dependencies=[Depends(require_role("admin", "embryologist"))])
async def import_file(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Accept CSV clinical datasets or blastocyst image ZIP archives."""
    return await _process_upload(file, db, current_user)


@router.post("/csv", status_code=status.HTTP_200_OK, dependencies=[Depends(require_role("admin", "embryologist"))])
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Backward-compatible CSV-only route using the full validation pipeline."""
    return await _process_upload(file, db, current_user, csv_only=True)


@router.get("/reports", dependencies=[Depends(require_role("admin", "embryologist"))])
def ingestion_reports(current_user: User = Depends(get_current_user)):
    ledger = DATA_ROOT / "reports" / "ingestion_report.csv"
    if not ledger.exists():
        return {"items": [], "total": 0}
    with ledger.open(encoding="utf-8") as stream:
        items = list(csv.DictReader(stream))
    items.reverse()
    return {"items": items[:200], "total": len(items)}


@router.get("/reports/{intake_id}", dependencies=[Depends(require_role("admin", "embryologist"))])
def ingestion_report(intake_id: str, current_user: User = Depends(get_current_user)):
    if not all(character.isalnum() or character == "-" for character in intake_id):
        raise HTTPException(status_code=400, detail="Invalid intake identifier")
    path = DATA_ROOT / "reports" / f"{intake_id}_summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Ingestion report not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/seed-from-disk", status_code=status.HTTP_200_OK, dependencies=[Depends(require_role("admin", "embryologist"))])
def seed_from_disk(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    path = Path(__file__).resolve().parents[3] / "docs" / "dataset" / "ET Summary - ET Data.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Bundled CSV was not found")
    result = intake_service.process(path.name, path.read_bytes(), uploaded_by=current_user.username)
    response = result.response()
    if result.quarantined:
        return {**response, "message": "Bundled CSV was quarantined"}
    return {**response, **_ingest_clean_csv(result, db, current_user), "message": "Bundled CSV validated and imported"}
