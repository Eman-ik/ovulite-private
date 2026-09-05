"""Pydantic schemas for Embryo CRUD operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class EmbryoBase(BaseModel):
    donor_id: Optional[int] = None
    sire_id: Optional[int] = None
    opu_id: Optional[int] = None
    ivf_batch_id: Optional[int] = None
    opu_date: Optional[date] = None
    stage: Optional[int] = None
    grade: Optional[int] = None
    fresh_or_frozen: Optional[str] = None
    cane_number: Optional[str] = None
    freezing_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 9):
            raise ValueError("Embryo stage must be between 1 and 9")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 4):
            raise ValueError("Embryo grade must be between 1 and 4")
        return v

    @field_validator("fresh_or_frozen")
    @classmethod
    def validate_fresh_or_frozen(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Fresh", "Frozen"):
            raise ValueError("Must be 'Fresh' or 'Frozen'")
        return v


class EmbryoCreate(EmbryoBase):
    pass


class EmbryoUpdate(BaseModel):
    donor_id: Optional[int] = None
    sire_id: Optional[int] = None
    opu_id: Optional[int] = None
    ivf_batch_id: Optional[int] = None
    opu_date: Optional[date] = None
    stage: Optional[int] = None
    grade: Optional[int] = None
    fresh_or_frozen: Optional[str] = None
    cane_number: Optional[str] = None
    freezing_date: Optional[date] = None
    notes: Optional[str] = None


class EmbryoResponse(EmbryoBase):
    embryo_id: int
    ai_grade: Optional[int] = None
    ai_viability: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
