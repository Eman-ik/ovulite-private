"""CRUD API endpoints for Donors."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.donor import Donor
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.donor import DonorCreate, DonorResponse, DonorUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[DonorResponse])
def list_donors(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List donors with pagination and optional search."""
    q = db.query(Donor).filter(Donor.organization_id == current_user.organization_id)
    if search:
        q = q.filter(
            Donor.tag_id.ilike(f"%{search}%")
            | Donor.breed.ilike(f"%{search}%")
        )
    total = q.count()
    items = q.order_by(Donor.donor_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{donor_id}", response_model=DonorResponse)
def get_donor(
    donor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single donor by ID."""
    donor = db.query(Donor).filter(
        Donor.donor_id == donor_id, Donor.organization_id == current_user.organization_id
    ).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return donor


@router.post("/", response_model=DonorResponse, status_code=status.HTTP_201_CREATED)
def create_donor(
    payload: DonorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new donor."""
    existing = db.query(Donor).filter(
        Donor.tag_id == payload.tag_id, Donor.organization_id == current_user.organization_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Donor with tag '{payload.tag_id}' already exists")
    donor = Donor(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(donor)
    db.commit()
    db.refresh(donor)
    return donor


@router.put("/{donor_id}", response_model=DonorResponse)
def update_donor(
    donor_id: int,
    payload: DonorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a donor."""
    donor = db.query(Donor).filter(
        Donor.donor_id == donor_id, Donor.organization_id == current_user.organization_id
    ).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(donor, key, value)
    db.commit()
    db.refresh(donor)
    return donor


@router.delete("/{donor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_donor(
    donor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a donor."""
    donor = db.query(Donor).filter(
        Donor.donor_id == donor_id, Donor.organization_id == current_user.organization_id
    ).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    db.delete(donor)
    db.commit()
