"""CRUD API endpoints for Recipients."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.recipient import Recipient
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.recipient import RecipientCreate, RecipientResponse, RecipientUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[RecipientResponse])
def list_recipients(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Recipient).filter(Recipient.organization_id == current_user.organization_id)
    if search:
        q = q.filter(
            Recipient.tag_id.ilike(f"%{search}%") | Recipient.farm_location.ilike(f"%{search}%")
        )
    total = q.count()
    items = q.order_by(Recipient.recipient_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{recipient_id}", response_model=RecipientResponse)
def get_recipient(recipient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = db.query(Recipient).filter(
        Recipient.recipient_id == recipient_id, Recipient.organization_id == current_user.organization_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return r


@router.post("/", response_model=RecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(
    payload: RecipientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    r = Recipient(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/{recipient_id}", response_model=RecipientResponse)
def update_recipient(
    recipient_id: int, payload: RecipientUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    r = db.query(Recipient).filter(
        Recipient.recipient_id == recipient_id, Recipient.organization_id == current_user.organization_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(r, key, value)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipient(recipient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = db.query(Recipient).filter(
        Recipient.recipient_id == recipient_id, Recipient.organization_id == current_user.organization_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    db.delete(r)
    db.commit()
