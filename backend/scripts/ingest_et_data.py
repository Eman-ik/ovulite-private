"""
CSV Ingestion Script — parses ET Data.csv into normalized database tables.

Handles:
- 488 ET records from the main CSV
- Data cleaning: dirty donor IDs, date parsing, duplicate columns
- Normalization into: donors, sires, recipients, technicians, protocols, embryos, et_transfers
- Missing value handling: '.' treated as NULL

Usage:
    python -m backend.scripts.ingest_et_data
    (or run directly from project root)
"""

import csv
import logging
import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Add project root so 'app' package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.protocol import Protocol
from app.models.recipient import Recipient
from app.models.sire import Sire
from app.models.technician import Technician

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Column indices in ET Data.csv
COL = {
    "et_number": 0,
    "lab": 1,
    "satellite": 2,
    "customer_id": 3,
    "et_date": 4,
    "farm_location": 5,
    "recipient_id_1": 6,
    "recipient_id_2": 7,
    "cow_or_heifer": 8,
    "heat_1": 9,
    "cl_side": 10,
    "cl_measure_mm": 11,
    "protocol": 12,
    "fresh_or_frozen": 13,
    "cane_number": 14,
    "freezing_date": 15,
    "et_tech": 16,
    "et_assistant": 17,
    "bc_score": 18,
    "embryo_stage": 19,
    "embryo_grade": 20,
    "heat_2": 21,
    "heat_day": 22,
    "pc1_date": 23,
    "pc1_result": 24,
    "pc2_date": 25,
    "pc2_result": 26,
    "fetal_sexing": 27,
    "opu_date": 28,
    "donor": 29,
    "donor_breed": 30,
    "donor_bw_epd": 31,
    "sire_name": 32,
    "sire_bw_epd": 33,
    "semen_type": 34,
    "sire_breed": 35,
    "client": 36,
    "dip_1": 37,
    "dip_2": 38,
}


def clean_str(val: str) -> str | None:
    """Strip whitespace, treat '.' and empty string as None."""
    val = val.strip()
    if val in ("", ".", "-", "N/A", "n/a"):
        return None
    return val


def parse_date(val: str) -> date | None:
    """Parse M/D/YYYY date format. Returns None for missing."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        # Try other formats
        for fmt in (
    "%m-%d-%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m/%d/%y",
    "%d/%m/%y",
):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    logger.warning("Unparseable date: %r", val)
    return None


def parse_decimal(val: str) -> Decimal | None:
    """Parse numeric string to Decimal. Returns None for missing."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        logger.warning("Unparseable decimal: %r", val)
        return None


def parse_int(val: str) -> int | None:
    """Parse integer string. Returns None for missing."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return int(float(s))
    except (ValueError, OverflowError):
        logger.warning("Unparseable int: %r", val)
        return None


def parse_bool_heat(val: str) -> bool | None:
    """Parse heat observed field. Various formats in data."""
    s = clean_str(val)
    if s is None:
        return None
    if s.lower() in ("yes", "y", "true", "1"):
        return True
    if s.lower() in ("no", "n", "false", "0"):
        return False
    return None


def normalize_cl_side(val: str) -> str | None:
    """Normalize CL side to Left/Right."""
    s = clean_str(val)
    if s is None:
        return None
    s_lower = s.lower()
    if s_lower == "left":
        return "Left"
    if s_lower == "right":
        return "Right"
    return s


def normalize_semen_type(val: str) -> str | None:
    """Normalize semen type to Conventional/Sexed/Unknown."""
    s = clean_str(val)
    if s is None:
        return None
    s_lower = s.lower()
    if "conventional" in s_lower:
        return "Conventional"
    if "sexed" in s_lower or "sorted" in s_lower or "female" in s_lower:
        return "Sexed"
    return "Unknown"


def normalize_pc_result(val: str) -> str | None:
    """Normalize pregnancy check result."""
    s = clean_str(val)
    if s is None:
        return None
    s_lower = s.lower()
    if "pregnant" in s_lower:
        return "Pregnant"
    if "open" in s_lower:
        return "Open"
    if "recheck" in s_lower:
        return "Recheck"
    return s


def normalize_donor_tag(val: str) -> str | None:
    """Clean donor tag. Some have dirty IDs (dates, etc.)."""
    s = clean_str(val)
    if s is None:
        return None
    # Some donor IDs are dates like 5/14/2025 — keep as-is, they're real tags
    return s


def get_row_value(row: list, col_key: str, col_dict: dict) -> str:
    """Safely get value from row by column name, returning empty string if out of range."""
    col_index = col_dict.get(col_key, -1)
    if col_index >= 0 and col_index < len(row):
        return row[col_index]
    return ""


def get_or_create_donor(db: Session, tag_id: str, breed: str | None, bw_epd: Decimal | None, organization_id: int) -> Donor:
    """Find existing donor by tag or create new one."""
    donor = db.query(Donor).filter(Donor.tag_id == tag_id, Donor.organization_id == organization_id).first()
    if donor:
        # Update breed/epd if we have better data
        if breed and not donor.breed:
            donor.breed = breed
        if bw_epd is not None and donor.birth_weight_epd is None:
            donor.birth_weight_epd = bw_epd
        return donor
    donor = Donor(tag_id=tag_id, breed=breed, birth_weight_epd=bw_epd, organization_id=organization_id)
    db.add(donor)
    db.flush()
    return donor


def get_or_create_sire(
    db: Session, name: str, breed: str | None, bw_epd: Decimal | None, semen_type: str | None, organization_id: int
) -> Sire:
    """Find existing sire by name or create new one."""
    sire = db.query(Sire).filter(Sire.name == name, Sire.organization_id == organization_id).first()
    if sire:
        if breed and not sire.breed:
            sire.breed = breed
        if bw_epd is not None and sire.birth_weight_epd is None:
            sire.birth_weight_epd = bw_epd
        if semen_type and not sire.semen_type:
            sire.semen_type = semen_type
        return sire
    sire = Sire(name=name, breed=breed, birth_weight_epd=bw_epd, semen_type=semen_type, organization_id=organization_id)
    db.add(sire)
    db.flush()
    return sire


def get_or_create_recipient(
    db: Session, tag_id: str, farm_location: str | None, cow_or_heifer: str | None, organization_id: int
) -> Recipient:
    """Find existing recipient by tag + farm or create new one."""
    # Recipients may share tag IDs across farms, so match on tag_id + farm
    q = db.query(Recipient).filter(Recipient.tag_id == tag_id, Recipient.organization_id == organization_id)
    if farm_location:
        q = q.filter(Recipient.farm_location == farm_location)
    recipient = q.first()
    if recipient:
        return recipient
    recipient = Recipient(tag_id=tag_id, farm_location=farm_location, cow_or_heifer=cow_or_heifer, organization_id=organization_id)
    db.add(recipient)
    db.flush()
    return recipient


def get_or_create_technician(db: Session, name: str, organization_id: int) -> Technician:
    """Find existing technician by name or create new one."""
    tech = db.query(Technician).filter(Technician.name == name, Technician.organization_id == organization_id).first()
    if tech:
        return tech
    tech = Technician(name=name, organization_id=organization_id)
    db.add(tech)
    db.flush()
    return tech


def get_or_create_protocol(db: Session, name: str, organization_id: int) -> Protocol:
    """Find existing protocol by name or create new one."""
    proto = db.query(Protocol).filter(Protocol.name == name, Protocol.organization_id == organization_id).first()
    if proto:
        return proto
    proto = Protocol(name=name, organization_id=organization_id)
    db.add(proto)
    db.flush()
    return proto


def ingest_et_data(csv_path: str, db: Session, organization_id: int = 1, commit: bool = True) -> dict:
    """Parse ET Data.csv and insert into normalized tables.

    Returns a summary dict with counts.
    """
    stats = {"rows_read": 0, "rows_ingested": 0, "rows_skipped": 0, "errors": []}

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        
        # Skip header rows and find the actual data header
        header = None
        raw_row_num = 0
        for row in reader:
            raw_row_num += 1
            # Skip empty rows
            if not row or all(cell.strip() == "" for cell in row):
                continue
            # Header labels are not at fixed positions across source exports.
            normalized_header = {cell.strip().lower() for cell in row}
            has_identifier = bool(normalized_header & {"# et", "et number", "sr. no", "sr. no."})
            if has_identifier and "et date" in normalized_header:
                header = row
                logger.info("Found data header at row %d: %d columns", raw_row_num, len(header))
                break
        
        if not header:
            logger.error("Could not find data header in CSV file")
            return stats
        
        for raw_row_num, row in enumerate(reader, start=raw_row_num+1):
            # Skip empty rows
            if not row or all(cell.strip() == "" for cell in row):
                continue
            
            # Skip rows that don't have enough columns or have invalid data
            if len(row) < len(COL) - 10:  # Allow some column variance
                stats["rows_skipped"] += 1
                continue
            
            et_num_str = row[COL["et_number"]].strip() if len(row) > COL["et_number"] else ""
            if not et_num_str:
                continue

            stats["rows_read"] += 1

            try:
                et_number = parse_int(et_num_str)

                # --- Donor ---
                donor_tag = normalize_donor_tag(row[COL["donor"]] if len(row) > COL["donor"] else "")
                donor = None
                if donor_tag:
                    donor_breed = clean_str(row[COL["donor_breed"]] if len(row) > COL["donor_breed"] else "")
                    donor_bw_epd = parse_decimal(row[COL["donor_bw_epd"]] if len(row) > COL["donor_bw_epd"] else "")
                    # Filter out dirty breed values (dates, IDs)
                    if donor_breed and ("/" in donor_breed or donor_breed.isdigit()):
                        logger.warning("Row %d: dirty donor breed %r for donor %s, setting to None", raw_row_num, donor_breed, donor_tag)
                        donor_breed = None
                    donor = get_or_create_donor(db, donor_tag, donor_breed, donor_bw_epd, organization_id)

                # --- Sire ---
                sire_name = clean_str(get_row_value(row, "sire_name", COL))
                sire = None
                if sire_name:
                    sire_breed = clean_str(get_row_value(row, "sire_breed", COL))
                    sire_bw_epd = parse_decimal(get_row_value(row, "sire_bw_epd", COL))
                    semen_type = normalize_semen_type(get_row_value(row, "semen_type", COL))
                    sire = get_or_create_sire(db, sire_name, sire_breed, sire_bw_epd, semen_type, organization_id)

                # --- Recipient ---
                recip_tag = clean_str(get_row_value(row, "recipient_id_1", COL))
                recipient = None
                if recip_tag:
                    farm = clean_str(get_row_value(row, "farm_location", COL))
                    cow_heifer = clean_str(get_row_value(row, "cow_or_heifer", COL))
                    recipient = get_or_create_recipient(db, recip_tag, farm, cow_heifer, organization_id)

                # --- Technician ---
                tech_name = clean_str(get_row_value(row, "et_tech", COL))
                technician = None
                if tech_name:
                    technician = get_or_create_technician(db, tech_name, organization_id)

                # --- Protocol ---
                proto_name = clean_str(get_row_value(row, "protocol", COL))
                protocol = None
                if proto_name:
                    protocol = get_or_create_protocol(db, proto_name, organization_id)

                # --- Embryo ---
                embryo = Embryo(
                    organization_id=organization_id,
                    donor_id=donor.donor_id if donor else None,
                    sire_id=sire.sire_id if sire else None,
                    opu_date=parse_date(get_row_value(row, "opu_date", COL)),
                    stage=parse_int(get_row_value(row, "embryo_stage", COL)),
                    grade=parse_int(get_row_value(row, "embryo_grade", COL)),
                    fresh_or_frozen=clean_str(get_row_value(row, "fresh_or_frozen", COL)),
                    cane_number=clean_str(get_row_value(row, "cane_number", COL)),
                    freezing_date=parse_date(get_row_value(row, "freezing_date", COL)),
                )
                db.add(embryo)
                db.flush()

                # --- ET Transfer ---
                et_date = parse_date(get_row_value(row, "et_date", COL))
                if et_date is None:
                    raw_date = get_row_value(row, "et_date", COL)
                    stats["rows_skipped"] += 1
                    stats["errors"].append(f"Row {raw_row_num}: invalid or missing ET date: {raw_date}")
                    continue

                transfer = ETTransfer(
                    organization_id=organization_id,
                    et_number=et_number,
                    lab=clean_str(get_row_value(row, "lab", COL)),
                    satellite=clean_str(get_row_value(row, "satellite", COL)),
                    customer_id=clean_str(get_row_value(row, "customer_id", COL)),
                    et_date=et_date,
                    farm_location=clean_str(get_row_value(row, "farm_location", COL)),
                    recipient_id=recipient.recipient_id if recipient else None,
                    bc_score=parse_decimal(get_row_value(row, "bc_score", COL)),
                    cl_side=normalize_cl_side(get_row_value(row, "cl_side", COL)),
                    cl_measure_mm=parse_decimal(get_row_value(row, "cl_measure_mm", COL)),
                    protocol_id=protocol.protocol_id if protocol else None,
                    heat_observed=parse_bool_heat(get_row_value(row, "heat_1", COL)),
                    heat_day=parse_int(get_row_value(row, "heat_day", COL)),
                    embryo_id=embryo.embryo_id,
                    technician_id=technician.technician_id if technician else None,
                    assistant_name=clean_str(get_row_value(row, "et_assistant", COL)),
                    pc1_date=parse_date(get_row_value(row, "pc1_date", COL)),
                    pc1_result=normalize_pc_result(get_row_value(row, "pc1_result", COL)),
                    pc2_date=parse_date(get_row_value(row, "pc2_date", COL)),
                    pc2_result=normalize_pc_result(get_row_value(row, "pc2_result", COL)),
                    fetal_sexing=clean_str(get_row_value(row, "fetal_sexing", COL)),
                    days_in_pregnancy=parse_int(get_row_value(row, "dip_1", COL)),
                )
                db.add(transfer)
                stats["rows_ingested"] += 1

            except Exception as exc:
                stats["rows_skipped"] += 1
                stats["errors"].append(f"Row {raw_row_num}: {exc}")
                logger.error("Row %d failed: %s", row_num, exc)

    if commit:
        db.commit()
    return stats


def main():
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "dataset", "ET Summary - ET Data.csv"
    )
    csv_path = os.path.normpath(csv_path)

    if not os.path.exists(csv_path):
        logger.error("CSV not found: %s", csv_path)
        sys.exit(1)

    logger.info("Starting ET Data ingestion from %s", csv_path)

    db = SessionLocal()
    try:
        # Check if data already exists
        existing = db.query(ETTransfer).count()
        if existing > 0:
            logger.warning("Database already has %d transfers. Skipping ingestion.", existing)
            logger.info("To re-ingest, truncate the tables first.")
            return

        stats = ingest_et_data(csv_path, db)

        logger.info("=== Ingestion Complete ===")
        logger.info("Rows read: %d", stats["rows_read"])
        logger.info("Rows ingested: %d", stats["rows_ingested"])
        logger.info("Rows skipped: %d", stats["rows_skipped"])
        logger.info("Donors: %d", db.query(Donor).count())
        logger.info("Sires: %d", db.query(Sire).count())
        logger.info("Recipients: %d", db.query(Recipient).count())
        logger.info("Technicians: %d", db.query(Technician).count())
        logger.info("Protocols: %d", db.query(Protocol).count())
        logger.info("Embryos: %d", db.query(Embryo).count())
        logger.info("Transfers: %d", db.query(ETTransfer).count())

        if stats["errors"]:
            logger.warning("Errors (%d):", len(stats["errors"]))
            for err in stats["errors"][:20]:
                logger.warning("  %s", err)
    finally:
        db.close()


if __name__ == "__main__":
    main()
