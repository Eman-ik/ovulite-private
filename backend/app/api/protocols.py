"""CRUD API endpoints for Protocols."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.protocol import Protocol
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.protocol import ProtocolCreate, ProtocolResponse, ProtocolUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ProtocolResponse])
def list_protocols(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Protocol).filter(Protocol.organization_id == current_user.organization_id)
    total = q.count()
    items = q.order_by(Protocol.protocol_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{protocol_id}", response_model=ProtocolResponse)
def get_protocol(protocol_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Protocol).filter(
        Protocol.protocol_id == protocol_id, Protocol.organization_id == current_user.organization_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return p


@router.post("/", response_model=ProtocolResponse, status_code=status.HTTP_201_CREATED)
def create_protocol(
    payload: ProtocolCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    p = Protocol(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{protocol_id}", response_model=ProtocolResponse)
def update_protocol(
    protocol_id: int, payload: ProtocolUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    p = db.query(Protocol).filter(
        Protocol.protocol_id == protocol_id, Protocol.organization_id == current_user.organization_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Protocol not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    return p
