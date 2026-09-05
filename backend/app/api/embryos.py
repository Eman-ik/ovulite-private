"""CRUD API endpoints for Embryos."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.embryo import Embryo
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.embryo import EmbryoCreate, EmbryoResponse, EmbryoUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[EmbryoResponse])
def list_embryos(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    donor_id: Optional[int] = None,
    sire_id: Optional[int] = None,
    fresh_or_frozen: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Embryo).filter(Embryo.organization_id == current_user.organization_id)
    if donor_id is not None:
        q = q.filter(Embryo.donor_id == donor_id)
    if sire_id is not None:
        q = q.filter(Embryo.sire_id == sire_id)
    if fresh_or_frozen:
        q = q.filter(Embryo.fresh_or_frozen == fresh_or_frozen)
    total = q.count()
    items = q.order_by(Embryo.embryo_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{embryo_id}", response_model=EmbryoResponse)
def get_embryo(embryo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    e = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Embryo not found")
    return e


@router.post("/", response_model=EmbryoResponse, status_code=status.HTTP_201_CREATED)
def create_embryo(
    payload: EmbryoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    e = Embryo(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.put("/{embryo_id}", response_model=EmbryoResponse)
def update_embryo(
    embryo_id: int, payload: EmbryoUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    e = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Embryo not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(e, key, value)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{embryo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_embryo(embryo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    e = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Embryo not found")
    db.delete(e)
    db.commit()
