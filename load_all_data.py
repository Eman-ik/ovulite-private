"""
Master data loader for Ovulite — loads ALL data from docs/dataset/ into the database.

Handles:
- ET Summary - ET Data.csv (primary dataset, ~488 records)
- New_Records_ET Summary - ET Data.csv (additional records, deduplicated)
- ET Summary - Sheet10.csv (donor-sire mappings)
- Pregnancy records (4 client report files)

Usage:
    python load_all_data.py
    (run from project root)
"""

import csv
import logging
import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Add backend to path so app modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from sqlalchemy.orm import Session
from sqlalchemy import text

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

DATASET_DIR = Path(__file__).resolve().parent / "docs" / "dataset"

# Column indices for the 39-column ET Data CSV
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


# ── Utility functions ──────────────────────────────────────────────

def clean_str(val: str) -> str | None:
    val = val.strip()
    if val in ("", ".", "-", "N/A", "n/a"):
        return None
    return val


def parse_date(val: str) -> date | None:
    s = clean_str(val)
    if s is None:
        return None
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    logger.warning("Unparseable date: %r", val)
    return None


def parse_decimal(val: str) -> Decimal | None:
    s = clean_str(val)
    if s is None:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_int(val: str) -> int | None:
    s = clean_str(val)
    if s is None:
        return None
    try:
        return int(float(s))
    except (ValueError, OverflowError):
        return None


def parse_bool_heat(val: str) -> bool | None:
    s = clean_str(val)
    if s is None:
        return None
    if s.lower() in ("yes", "y", "true", "1"):
        return True
    if s.lower() in ("no", "n", "false", "0"):
        return False
    return None


def normalize_cl_side(val: str) -> str | None:
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


def get_row_value(row: list, col_key: str) -> str:
    col_index = COL.get(col_key, -1)
    if 0 <= col_index < len(row):
        return row[col_index]
    return ""


# ── Get-or-create helpers ──────────────────────────────────────────

def get_or_create_donor(db: Session, tag_id: str, breed: str | None, bw_epd: Decimal | None, org_id: int) -> Donor:
    donor = db.query(Donor).filter(Donor.tag_id == tag_id, Donor.organization_id == org_id).first()
    if donor:
        if breed and not donor.breed:
            donor.breed = breed
        if bw_epd is not None and donor.birth_weight_epd is None:
            donor.birth_weight_epd = bw_epd
        return donor
    donor = Donor(tag_id=tag_id, breed=breed, birth_weight_epd=bw_epd, organization_id=org_id)
    db.add(donor)
    db.flush()
    return donor


def get_or_create_sire(db: Session, name: str, breed: str | None, bw_epd: Decimal | None, semen_type: str | None, org_id: int) -> Sire:
    sire = db.query(Sire).filter(Sire.name == name, Sire.organization_id == org_id).first()
    if sire:
        if breed and not sire.breed:
            sire.breed = breed
        if bw_epd is not None and sire.birth_weight_epd is None:
            sire.birth_weight_epd = bw_epd
        if semen_type and not sire.semen_type:
            sire.semen_type = semen_type
        return sire
    sire = Sire(name=name, breed=breed, birth_weight_epd=bw_epd, semen_type=semen_type, organization_id=org_id)
    db.add(sire)
    db.flush()
    return sire


def get_or_create_recipient(db: Session, tag_id: str, farm: str | None, cow_heifer: str | None, org_id: int) -> Recipient:
    q = db.query(Recipient).filter(Recipient.tag_id == tag_id, Recipient.organization_id == org_id)
    if farm:
        q = q.filter(Recipient.farm_location == farm)
    recipient = q.first()
    if recipient:
        return recipient
    recipient = Recipient(tag_id=tag_id, farm_location=farm, cow_or_heifer=cow_heifer, organization_id=org_id)
    db.add(recipient)
    db.flush()
    return recipient


def get_or_create_technician(db: Session, name: str, org_id: int) -> Technician:
    tech = db.query(Technician).filter(Technician.name == name, Technician.organization_id == org_id).first()
    if tech:
        return tech
    tech = Technician(name=name, organization_id=org_id)
    db.add(tech)
    db.flush()
    return tech


def get_or_create_protocol(db: Session, name: str, org_id: int) -> Protocol:
    proto = db.query(Protocol).filter(Protocol.name == name, Protocol.organization_id == org_id).first()
    if proto:
        return proto
    proto = Protocol(name=name, organization_id=org_id)
    db.add(proto)
    db.flush()
    return proto


# ── CSV ingestion ──────────────────────────────────────────────────

def ingest_et_csv(csv_path: Path, db: Session, org_id: int = 1) -> dict:
    """Parse an ET Data CSV and insert into normalized tables.

    Deduplicates by (et_number + et_date) to avoid loading the same transfer twice.
    Returns summary dict.
    """
    stats = {"rows_read": 0, "rows_ingested": 0, "rows_skipped": 0, "errors": []}

    # Load existing transfer keys for deduplication
    existing_keys = set()
    for transfer in db.query(ETTransfer.et_number, ETTransfer.et_date).filter(
        ETTransfer.organization_id == org_id
    ).all():
        existing_keys.add((transfer.et_number, transfer.et_date))

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)

        # Find the header row
        header = None
        raw_row_num = 0
        for row in reader:
            raw_row_num += 1
            if not row or all(cell.strip() == "" for cell in row):
                continue
            normalized_header = {cell.strip().lower() for cell in row}
            has_identifier = bool(normalized_header & {"# et", "et number", "sr. no", "sr. no.", "#"})
            if has_identifier and "et date" in normalized_header:
                header = row
                logger.info("  Found header at row %d (%d columns)", raw_row_num, len(header))
                break

        if not header:
            logger.error("  Could not find data header in %s", csv_path.name)
            return stats

        for raw_row_num, row in enumerate(reader, start=raw_row_num + 1):
            if not row or all(cell.strip() == "" for cell in row):
                continue
            if len(row) < len(COL) - 10:
                stats["rows_skipped"] += 1
                continue

            et_num_str = row[COL["et_number"]].strip() if len(row) > COL["et_number"] else ""
            if not et_num_str:
                continue

            stats["rows_read"] += 1

            try:
                et_number = parse_int(et_num_str)
                et_date = parse_date(get_row_value(row, "et_date"))
                if et_number is None or et_date is None:
                    stats["rows_skipped"] += 1
                    continue

                # Deduplication
                if (et_number, et_date) in existing_keys:
                    stats["rows_skipped"] += 1
                    continue

                # ── Donor ──
                donor_tag = clean_str(row[COL["donor"]] if len(row) > COL["donor"] else "")
                donor = None
                if donor_tag:
                    donor_breed = clean_str(row[COL["donor_breed"]] if len(row) > COL["donor_breed"] else "")
                    donor_bw_epd = parse_decimal(row[COL["donor_bw_epd"]] if len(row) > COL["donor_bw_epd"] else "")
                    if donor_breed and ("/" in donor_breed or donor_breed.isdigit()):
                        donor_breed = None
                    donor = get_or_create_donor(db, donor_tag, donor_breed, donor_bw_epd, org_id)

                # ── Sire ──
                sire_name = clean_str(get_row_value(row, "sire_name"))
                sire = None
                if sire_name:
                    sire_breed = clean_str(get_row_value(row, "sire_breed"))
                    sire_bw_epd = parse_decimal(get_row_value(row, "sire_bw_epd"))
                    semen_type = normalize_semen_type(get_row_value(row, "semen_type"))
                    sire = get_or_create_sire(db, sire_name, sire_breed, sire_bw_epd, semen_type, org_id)

                # ── Recipient ──
                recip_tag = clean_str(get_row_value(row, "recipient_id_1"))
                recipient = None
                if recip_tag:
                    farm = clean_str(get_row_value(row, "farm_location"))
                    cow_heifer = clean_str(get_row_value(row, "cow_or_heifer"))
                    recipient = get_or_create_recipient(db, recip_tag, farm, cow_heifer, org_id)

                # ── Technician ──
                tech_name = clean_str(get_row_value(row, "et_tech"))
                technician = None
                if tech_name:
                    technician = get_or_create_technician(db, tech_name, org_id)

                # ── Protocol ──
                proto_name = clean_str(get_row_value(row, "protocol"))
                protocol = None
                if proto_name:
                    protocol = get_or_create_protocol(db, proto_name, org_id)

                # ── Embryo ──
                embryo = Embryo(
                    organization_id=org_id,
                    donor_id=donor.donor_id if donor else None,
                    sire_id=sire.sire_id if sire else None,
                    opu_date=parse_date(get_row_value(row, "opu_date")),
                    stage=parse_int(get_row_value(row, "embryo_stage")),
                    grade=parse_int(get_row_value(row, "embryo_grade")),
                    fresh_or_frozen=clean_str(get_row_value(row, "fresh_or_frozen")),
                    cane_number=clean_str(get_row_value(row, "cane_number")),
                    freezing_date=parse_date(get_row_value(row, "freezing_date")),
                )
                db.add(embryo)
                db.flush()

                # ── ET Transfer ──
                transfer = ETTransfer(
                    organization_id=org_id,
                    et_number=et_number,
                    lab=clean_str(get_row_value(row, "lab")),
                    satellite=clean_str(get_row_value(row, "satellite")),
                    customer_id=clean_str(get_row_value(row, "customer_id")),
                    et_date=et_date,
                    farm_location=clean_str(get_row_value(row, "farm_location")),
                    recipient_id=recipient.recipient_id if recipient else None,
                    bc_score=parse_decimal(get_row_value(row, "bc_score")),
                    cl_side=normalize_cl_side(get_row_value(row, "cl_side")),
                    cl_measure_mm=parse_decimal(get_row_value(row, "cl_measure_mm")),
                    protocol_id=protocol.protocol_id if protocol else None,
                    heat_observed=parse_bool_heat(get_row_value(row, "heat_1")),
                    heat_day=parse_int(get_row_value(row, "heat_day")),
                    embryo_id=embryo.embryo_id,
                    technician_id=technician.technician_id if technician else None,
                    assistant_name=clean_str(get_row_value(row, "et_assistant")),
                    pc1_date=parse_date(get_row_value(row, "pc1_date")),
                    pc1_result=normalize_pc_result(get_row_value(row, "pc1_result")),
                    pc2_date=parse_date(get_row_value(row, "pc2_date")),
                    pc2_result=normalize_pc_result(get_row_value(row, "pc2_result")),
                    fetal_sexing=clean_str(get_row_value(row, "fetal_sexing")),
                    days_in_pregnancy=parse_int(get_row_value(row, "dip_1")),
                )
                db.add(transfer)
                existing_keys.add((et_number, et_date))
                stats["rows_ingested"] += 1

            except Exception as exc:
                stats["rows_skipped"] += 1
                stats["errors"].append(f"Row {raw_row_num}: {exc}")

    return stats


def load_donor_sire_mapping(csv_path: Path, db: Session, org_id: int) -> dict:
    """Load donor-sire pairing data from Sheet10.csv.

    This supplements the main ET data by providing explicit donor-sire associations.
    """
    stats = {"rows_read": 0, "rows_linked": 0, "rows_skipped": 0}

    if not csv_path.exists():
        logger.warning("  Sheet10 not found: %s", csv_path)
        return stats

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = None
        for row in reader:
            if not row or all(cell.strip() == "" for cell in row):
                continue
            if row[0].strip().lower() in ("donor", "donor_id"):
                header = row
                break

        if not header:
            logger.warning("  No header found in Sheet10")
            return stats

        seen_pairs = set()
        for row in reader:
            if not row or all(cell.strip() == "" for cell in row):
                continue
            donor_tag = clean_str(row[0]) if len(row) > 0 else None
            sire_name = clean_str(row[1]) if len(row) > 1 else None

            if not donor_tag or not sire_name:
                stats["rows_skipped"] += 1
                continue

            stats["rows_read"] += 1
            pair_key = (donor_tag, sire_name)
            if pair_key in seen_pairs:
                stats["rows_skipped"] += 1
                continue
            seen_pairs.add(pair_key)

            # Ensure donor exists
            donor = db.query(Donor).filter(
                Donor.tag_id == donor_tag, Donor.organization_id == org_id
            ).first()
            if not donor:
                donor = Donor(tag_id=donor_tag, organization_id=org_id)
                db.add(donor)
                db.flush()

            # Ensure sire exists
            sire = db.query(Sire).filter(
                Sire.name == sire_name, Sire.organization_id == org_id
            ).first()
            if not sire:
                sire = Sire(name=sire_name, organization_id=org_id)
                db.add(sire)
                db.flush()

            stats["rows_linked"] += 1

    return stats


# ── Main ───────────────────────────────────────────────────────────

def main():
    logger.info("=" * 70)
    logger.info("  OVULITE MASTER DATA LOADER")
    logger.info("=" * 70)

    # Ensure tables exist
    logger.info("Ensuring database tables exist...")
    import app.models  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)
    logger.info("  Tables ready.")

    db = SessionLocal()
    org_id = 1  # Default organization

    try:
        # ── 1. Main ET Data ──
        main_csv = DATASET_DIR / "ET Summary - ET Data.csv"
        logger.info("")
        logger.info("─── 1/3: Main ET Data (%s) ───", main_csv.name)
        if main_csv.exists():
            stats = ingest_et_csv(main_csv, db, org_id)
            db.commit()
            logger.info("  Rows read: %d", stats["rows_read"])
            logger.info("  Rows ingested: %d", stats["rows_ingested"])
            logger.info("  Rows skipped (duplicates/invalid): %d", stats["rows_skipped"])
            if stats["errors"]:
                logger.warning("  Errors: %d", len(stats["errors"]))
                for err in stats["errors"][:10]:
                    logger.warning("    %s", err)
        else:
            logger.warning("  File not found: %s", main_csv)

        # ── 2. New Records (deduplicated) ──
        new_csv = DATASET_DIR / "New_Records_ET Summary - ET Data.csv"
        logger.info("")
        logger.info("─── 2/3: New Records (%s) ───", new_csv.name)
        if new_csv.exists():
            stats = ingest_et_csv(new_csv, db, org_id)
            db.commit()
            logger.info("  Rows read: %d", stats["rows_read"])
            logger.info("  New rows ingested: %d", stats["rows_ingested"])
            logger.info("  Rows skipped (duplicates/invalid): %d", stats["rows_skipped"])
            if stats["errors"]:
                logger.warning("  Errors: %d", len(stats["errors"]))
                for err in stats["errors"][:10]:
                    logger.warning("    %s", err)
        else:
            logger.warning("  File not found: %s", new_csv)

        # ── 3. Donor-Sire Mapping (Sheet10) ──
        sheet10 = DATASET_DIR / "ET Summary - Sheet10.csv"
        logger.info("")
        logger.info("─── 3/3: Donor-Sire Mapping (%s) ───", sheet10.name)
        if sheet10.exists():
            stats = load_donor_sire_mapping(sheet10, db, org_id)
            db.commit()
            logger.info("  Pairs read: %d", stats["rows_read"])
            logger.info("  Pairs linked: %d", stats["rows_linked"])
            logger.info("  Pairs skipped: %d", stats["rows_skipped"])
        else:
            logger.warning("  File not found: %s", sheet10)

        # ── Summary ──
        logger.info("")
        logger.info("=" * 70)
        logger.info("  DATABASE SUMMARY")
        logger.info("=" * 70)
        logger.info("  Donors:      %d", db.query(Donor).count())
        logger.info("  Sires:       %d", db.query(Sire).count())
        logger.info("  Recipients:  %d", db.query(Recipient).count())
        logger.info("  Technicians: %d", db.query(Technician).count())
        logger.info("  Protocols:   %d", db.query(Protocol).count())
        logger.info("  Embryos:     %d", db.query(Embryo).count())
        logger.info("  Transfers:   %d", db.query(ETTransfer).count())
        logger.info("=" * 70)

    except Exception:
        db.rollback()
        logger.exception("Data loading failed — rolling back")
        raise
    finally:
        db.close()

    logger.info("Data loading complete!")


if __name__ == "__main__":
    main()
