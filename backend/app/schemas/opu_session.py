"""Pydantic schemas for OPU Session CRUD operations."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, computed_field, model_validator


class OPUSessionBase(BaseModel):
    donor_id: int
    opu_date: date
    technician_id: Optional[int] = None
    farm_location: Optional[str] = None
    total_follicles: Optional[int] = None
    oocytes_recovered: Optional[int] = None
    viable_oocytes: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_counts(self) -> "OPUSessionBase":
        if (
            self.total_follicles is not None
            and self.oocytes_recovered is not None
            and self.oocytes_recovered > self.total_follicles
        ):
            raise ValueError("oocytes_recovered cannot exceed total_follicles")
        if (
            self.oocytes_recovered is not None
            and self.viable_oocytes is not None
            and self.viable_oocytes > self.oocytes_recovered
        ):
            raise ValueError("viable_oocytes cannot exceed oocytes_recovered")
        return self


class OPUSessionCreate(OPUSessionBase):
    pass


class OPUSessionUpdate(BaseModel):
    donor_id: Optional[int] = None
    opu_date: Optional[date] = None
    technician_id: Optional[int] = None
    farm_location: Optional[str] = None
    total_follicles: Optional[int] = None
    oocytes_recovered: Optional[int] = None
    viable_oocytes: Optional[int] = None
    notes: Optional[str] = None


class OPUSessionResponse(OPUSessionBase):
    opu_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def recovery_rate(self) -> Optional[float]:
        """oocytes_recovered / total_follicles, as a fraction. None when either count is unknown."""
        if not self.total_follicles or self.oocytes_recovered is None:
            return None
        return round(self.oocytes_recovered / self.total_follicles, 4)
