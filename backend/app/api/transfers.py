"""CRUD API endpoints for ET Transfers (the central entity)."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.protocol import Protocol
from app.models.recipient import Recipient
from app.models.sire import Sire
from app.models.technician import Technician
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.et_transfer import (
    ETTransferCreate,
    ETTransferDetail,
    ETTransferResponse,
    ETTransferUpdate,
)

router = APIRouter()


def _clean_pregnancy_result(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"pregnant", "p", "positive"}:
        return "Pregnant"
    if normalized in {"open", "o", "negative"}:
        return "Open"
    if normalized in {"recheck", "pending"}:
        return "Recheck"
    return None


def _build_detail(t: ETTransfer) -> dict:
    """Build ETTransferDetail dict with joined entity names."""
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["pc1_result"] = _clean_pregnancy_result(t.pc1_result)
    d["donor_tag"] = t.embryo.donor.tag_id if t.embryo and t.embryo.donor else None
    d["donor_breed"] = t.embryo.donor.breed if t.embryo and t.embryo.donor else None
    d["sire_name"] = t.embryo.sire.name if t.embryo and t.embryo.sire else None
    d["recipient_tag"] = t.recipient.tag_id if t.recipient else None
    d["technician_name"] = t.technician.name if t.technician else None
    d["protocol_name"] = t.protocol.name if t.protocol else None
    d["embryo_stage"] = t.embryo.stage if t.embryo else None
    d["embryo_grade"] = t.embryo.grade if t.embryo else None
    d["fresh_or_frozen"] = t.embryo.fresh_or_frozen if t.embryo else None
    return d


@router.get("/", response_model=PaginatedResponse[ETTransferDetail])
def list_transfers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    protocol_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    pc1_result: Optional[str] = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List ET transfers with pagination, filters, and joined entity names."""
    q = db.query(ETTransfer).options(
        joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
        joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
        joinedload(ETTransfer.recipient),
        joinedload(ETTransfer.technician),
        joinedload(ETTransfer.protocol),
    )
    if search:
        q = q.filter(
            ETTransfer.customer_id.ilike(f"%{search}%")
            | ETTransfer.farm_location.ilike(f"%{search}%")
        )
    if protocol_id is not None:
        q = q.filter(ETTransfer.protocol_id == protocol_id)
    if technician_id is not None:
        q = q.filter(ETTransfer.technician_id == technician_id)
    if pc1_result:
        q = q.filter(ETTransfer.pc1_result == pc1_result)

    total = q.count()
    items = q.order_by(ETTransfer.transfer_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[_build_detail(t) for t in items],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{transfer_id}", response_model=ETTransferDetail)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    t = (
        db.query(ETTransfer)
        .options(
            joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
            joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
            joinedload(ETTransfer.recipient),
            joinedload(ETTransfer.technician),
            joinedload(ETTransfer.protocol),
        )
        .filter(ETTransfer.transfer_id == transfer_id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return _build_detail(t)


@router.post("/", response_model=ETTransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: ETTransferCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Create a new ET transfer record."""
    transfer = ETTransfer(**payload.model_dump())
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer


@router.put("/{transfer_id}", response_model=ETTransferResponse)
def update_transfer(
    transfer_id: int,
    payload: ETTransferUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    t = db.query(ETTransfer).filter(ETTransfer.transfer_id == transfer_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    t = db.query(ETTransfer).filter(ETTransfer.transfer_id == transfer_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    db.delete(t)
    db.commit()
