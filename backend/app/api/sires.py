"""CRUD API endpoints for Sires."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.sire import Sire
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.sire import SireCreate, SireResponse, SireUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[SireResponse])
def list_sires(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Sire).filter(Sire.organization_id == current_user.organization_id)
    if search:
        q = q.filter(Sire.name.ilike(f"%{search}%") | Sire.breed.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(Sire.sire_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{sire_id}", response_model=SireResponse)
def get_sire(sire_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sire = db.query(Sire).filter(
        Sire.sire_id == sire_id, Sire.organization_id == current_user.organization_id
    ).first()
    if not sire:
        raise HTTPException(status_code=404, detail="Sire not found")
    return sire


@router.post("/", response_model=SireResponse, status_code=status.HTTP_201_CREATED)
def create_sire(
    payload: SireCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    sire = Sire(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(sire)
    db.commit()
    db.refresh(sire)
    return sire


@router.put("/{sire_id}", response_model=SireResponse)
def update_sire(
    sire_id: int, payload: SireUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    sire = db.query(Sire).filter(
        Sire.sire_id == sire_id, Sire.organization_id == current_user.organization_id
    ).first()
    if not sire:
        raise HTTPException(status_code=404, detail="Sire not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sire, key, value)
    db.commit()
    db.refresh(sire)
    return sire


@router.delete("/{sire_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sire(sire_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sire = db.query(Sire).filter(
        Sire.sire_id == sire_id, Sire.organization_id == current_user.organization_id
    ).first()
    if not sire:
        raise HTTPException(status_code=404, detail="Sire not found")
    db.delete(sire)
    db.commit()
