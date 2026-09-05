"""CRUD API endpoints for Technicians."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.technician import Technician
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.technician import TechnicianCreate, TechnicianResponse, TechnicianUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[TechnicianResponse])
def list_technicians(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Technician).filter(Technician.organization_id == current_user.organization_id)
    total = q.count()
    items = q.order_by(Technician.technician_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{technician_id}", response_model=TechnicianResponse)
def get_technician(technician_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t = db.query(Technician).filter(
        Technician.technician_id == technician_id, Technician.organization_id == current_user.organization_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    return t


@router.post("/", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED)
def create_technician(
    payload: TechnicianCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    existing = db.query(Technician).filter(
        Technician.name == payload.name, Technician.organization_id == current_user.organization_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Technician named '{payload.name}' already exists")
    t = Technician(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{technician_id}", response_model=TechnicianResponse)
def update_technician(
    technician_id: int, payload: TechnicianUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    t = db.query(Technician).filter(
        Technician.technician_id == technician_id, Technician.organization_id == current_user.organization_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return t
