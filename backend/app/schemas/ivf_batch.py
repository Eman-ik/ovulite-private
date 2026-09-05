"""Pydantic schemas for IVF Batch CRUD operations."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, computed_field, model_validator


class IVFBatchBase(BaseModel):
    opu_id: int
    sire_id: Optional[int] = None
    ivf_date: Optional[date] = None
    oocytes_used: Optional[int] = None
    mature_oocytes: Optional[int] = None
    cleaved_embryos: Optional[int] = None
    blastocysts: Optional[int] = None
    degenerated_embryos: Optional[int] = None
    culture_media: Optional[str] = None
    embryologist_id: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_counts(self) -> "IVFBatchBase":
        if (
            self.oocytes_used is not None
            and self.mature_oocytes is not None
            and self.mature_oocytes > self.oocytes_used
        ):
            raise ValueError("mature_oocytes cannot exceed oocytes_used")
        if (
            self.oocytes_used is not None
            and self.cleaved_embryos is not None
            and self.cleaved_embryos > self.oocytes_used
        ):
            raise ValueError("cleaved_embryos cannot exceed oocytes_used")
        if (
            self.cleaved_embryos is not None
            and self.blastocysts is not None
            and self.blastocysts > self.cleaved_embryos
        ):
            raise ValueError("blastocysts cannot exceed cleaved_embryos")
        return self


class IVFBatchCreate(IVFBatchBase):
    pass


class IVFBatchUpdate(BaseModel):
    opu_id: Optional[int] = None
    sire_id: Optional[int] = None
    ivf_date: Optional[date] = None
    oocytes_used: Optional[int] = None
    mature_oocytes: Optional[int] = None
    cleaved_embryos: Optional[int] = None
    blastocysts: Optional[int] = None
    degenerated_embryos: Optional[int] = None
    culture_media: Optional[str] = None
    embryologist_id: Optional[int] = None
    notes: Optional[str] = None


class IVFBatchResponse(IVFBatchBase):
    ivf_batch_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def cleavage_rate(self) -> Optional[float]:
        """cleaved_embryos / oocytes_used. None when either count is unknown."""
        if not self.oocytes_used or self.cleaved_embryos is None:
            return None
        return round(self.cleaved_embryos / self.oocytes_used, 4)

    @computed_field
    @property
    def blastocyst_rate(self) -> Optional[float]:
        """blastocysts / oocytes_used. None when either count is unknown."""
        if not self.oocytes_used or self.blastocysts is None:
            return None
        return round(self.blastocysts / self.oocytes_used, 4)
