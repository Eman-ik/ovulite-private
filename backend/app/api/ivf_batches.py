"""CRUD API endpoints for IVF Batches."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.ivf_batch import IVFBatch
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.ivf_batch import IVFBatchCreate, IVFBatchResponse, IVFBatchUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[IVFBatchResponse])
def list_ivf_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    opu_id: Optional[int] = None,
    sire_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List IVF batches with pagination, optionally filtered by OPU session or sire."""
    q = db.query(IVFBatch).filter(IVFBatch.organization_id == current_user.organization_id)
    if opu_id is not None:
        q = q.filter(IVFBatch.opu_id == opu_id)
    if sire_id is not None:
        q = q.filter(IVFBatch.sire_id == sire_id)
    total = q.count()
    items = q.order_by(IVFBatch.ivf_batch_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{ivf_batch_id}", response_model=IVFBatchResponse)
def get_ivf_batch(ivf_batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    b = db.query(IVFBatch).filter(
        IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == current_user.organization_id
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="IVF batch not found")
    return b


@router.post("/", response_model=IVFBatchResponse, status_code=status.HTTP_201_CREATED)
def create_ivf_batch(
    payload: IVFBatchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    b = IVFBatch(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.put("/{ivf_batch_id}", response_model=IVFBatchResponse)
def update_ivf_batch(
    ivf_batch_id: int, payload: IVFBatchUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    b = db.query(IVFBatch).filter(
        IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == current_user.organization_id
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="IVF batch not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(b, key, value)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/{ivf_batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ivf_batch(ivf_batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    b = db.query(IVFBatch).filter(
        IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == current_user.organization_id
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="IVF batch not found")
    db.delete(b)
    db.commit()
