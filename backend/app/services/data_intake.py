"""Immutable, schema-driven CSV and image-ZIP intake service."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


BASE = Path(__file__).resolve().parents[2]
DATA_ROOT = BASE / "data"
SCHEMA_PATH = BASE / "config" / "intake_schema.yaml"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]", "_", Path(name).name)[:180] or "upload.bin"


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV encoding is unreadable (tried UTF-8 and CP1252)")


def _category(filename: str, file_type: str) -> str:
    value = filename.lower()
    if "new_records" in value:
        return "suspect"
    if file_type == "zip" and ("blastocyst" in value or "image" in value):
        return "image"
    if "et_data" in value or "sheet10" in value:
        return "trusted"
    return "unknown"


def _empty(value: Any) -> bool:
    return value is None or str(value).strip() in {"", ".", "-", "N/A", "n/a", "null", "None"}


def _valid_type(value: str, expected: str) -> bool:
    try:
        if expected == "integer":
            return float(value).is_integer()
        if expected in {"float", "number"}:
            float(value)
            return True
        if expected in {"date", "datetime"}:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
    except (ValueError, TypeError, OverflowError):
        if expected in {"date", "datetime"}:
            for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    pass
        return False
    return True


@dataclass
class IntakeResult:
    metadata: dict[str, Any]
    summary: dict[str, Any]
    clean_csv_path: Path | None = None
    quarantined: bool = False

    def response(self) -> dict[str, Any]:
        return {"metadata": self.metadata, "summary": self.summary, "quarantined": self.quarantined}


class DataIntakeService:
    def __init__(self, data_root: Path = DATA_ROOT, schema_path: Path = SCHEMA_PATH):
        self.root = data_root
        self.schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        for folder in ("raw", "staging/quarantined", "staging/flagged", "processed", "reports", "reports/notifications", "image_raw"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def process(self, filename: str, content: bytes, uploaded_by: str | None = None) -> IntakeResult:
        now = datetime.now(timezone.utc)
        intake_id = str(uuid.uuid4())
        safe_name = _safe_name(filename)
        extension = Path(safe_name).suffix.lower()
        file_type = "csv" if extension in {".csv", ".tsv"} else "zip" if extension == ".zip" else "unknown"
        raw_dir = self.root / "raw" / now.strftime("%Y%m%d")
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{now:%H%M%S}_{intake_id}_{safe_name}"
        raw_path.write_bytes(content)
        raw_path.chmod(0o444)
        metadata = {
            "intake_id": intake_id, "file_name": safe_name, "file_type": file_type,
            "upload_timestamp": now.isoformat(), "file_size": len(content),
            "checksum": hashlib.sha256(content).hexdigest(), "source_category": _category(safe_name, file_type),
            "raw_path": str(raw_path.relative_to(self.root)), "uploaded_by": uploaded_by,
            "schema_version": self.schema.get("version", "unknown"),
        }
        if file_type == "unknown":
            return self._quarantine(content, metadata, "Unsupported file type")
        if metadata["source_category"] == "suspect":
            return self._quarantine(content, metadata, "New_Records source is quarantined by policy")
        if file_type == "zip":
            return self._process_zip(content, metadata)
        return self._process_csv(content, metadata)

    def _quarantine(self, content: bytes, metadata: dict[str, Any], reason: str) -> IntakeResult:
        target = self.root / "staging" / "quarantined" / f"{metadata['intake_id']}_{metadata['file_name']}"
        target.write_bytes(content)
        metadata.update({"is_corrupted": True, "quarantine_path": str(target.relative_to(self.root)), "quarantine_reason": reason})
        summary = {"status": "QUARANTINED", "original_row_count": metadata.get("row_count"), "clean_rows": 0, "warning_rows": 0, "critical_rows": 0, "reason": reason}
        self._write_reports(metadata, summary, [])
        return IntakeResult(metadata, summary, quarantined=True)

    def _process_zip(self, content: bytes, metadata: dict[str, Any]) -> IntakeResult:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                bad = archive.testzip()
                if bad:
                    return self._quarantine(content, metadata, f"Corrupted ZIP member: {bad}")
                members = [item for item in archive.infolist() if not item.is_dir()]
                unsafe = [m.filename for m in members if Path(m.filename).is_absolute() or ".." in Path(m.filename).parts]
                if unsafe:
                    return self._quarantine(content, metadata, "ZIP contains unsafe paths")
                if any(m.flag_bits & 0x1 for m in members):
                    return self._quarantine(content, metadata, "Encrypted ZIP files are not accepted")
                if sum(m.file_size for m in members) > 1_000_000_000:
                    return self._quarantine(content, metadata, "ZIP expands beyond the 1 GB safety limit")
                images = [m for m in members if Path(m.filename).suffix.lower() in IMAGE_EXTENSIONS]
                if not images:
                    return self._quarantine(content, metadata, "ZIP contains no supported images")
                destination = self.root / "image_raw" / metadata["intake_id"]
                destination.mkdir(parents=True, exist_ok=True)
                for member in images:
                    target = destination / _safe_name(Path(member.filename).name)
                    with archive.open(member) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
        except (zipfile.BadZipFile, OSError) as exc:
            return self._quarantine(content, metadata, f"Invalid ZIP: {exc}")
        metadata.update({"row_count": None, "image_count": len(images), "image_path": str(destination.relative_to(self.root)), "is_corrupted": False})
        summary = {"status": "IMAGE_ACCEPTED", "image_count": len(images), "clean_rows": 0, "warning_rows": 0, "critical_rows": 0}
        self._write_reports(metadata, summary, [])
        return IntakeResult(metadata, summary)

    def _process_csv(self, content: bytes, metadata: dict[str, Any]) -> IntakeResult:
        try:
            text, encoding = _decode(content)
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
            reader = csv.DictReader(io.StringIO(text), dialect=dialect)
            rows = list(reader)
        except (ValueError, csv.Error) as exc:
            return self._quarantine(content, metadata, f"Unreadable CSV: {exc}")
        headers = [str(name).strip() for name in (reader.fieldnames or []) if name]
        metadata.update({"row_count": len(rows), "encoding": encoding, "is_corrupted": False})
        resolved: dict[str, str | None] = {}
        missing_columns = []
        for canonical, rule in self.schema["columns"].items():
            source = next((name for name in rule.get("source_names", [canonical]) if name in headers), None)
            resolved[canonical] = source
            if rule.get("required") and source is None:
                missing_columns.append(canonical)
        if missing_columns:
            return self._quarantine(content, metadata, f"Missing required columns: {', '.join(missing_columns)}")

        duplicate_indices = set()
        fingerprints: dict[tuple, int] = {}
        for index, row in enumerate(rows):
            fingerprint = tuple((header, row.get(header, "")) for header in headers)
            if fingerprint in fingerprints:
                duplicate_indices.update({fingerprints[fingerprint], index})
            else:
                fingerprints[fingerprint] = index
        constant_grade = False
        grade_source = resolved.get("embryo_grade")
        if grade_source:
            grades = {row.get(grade_source, "").strip() for row in rows if not _empty(row.get(grade_source))}
            constant_grade = len(grades) <= 1 and bool(rows)

        results, accepted, rejected, flagged = [], [], [], []
        for index, row in enumerate(rows):
            level, messages = "OK", []
            for canonical, rule in self.schema["columns"].items():
                source, value = resolved[canonical], row.get(resolved[canonical], "") if resolved[canonical] else ""
                if rule.get("required") and _empty(value):
                    level, messages = "CRITICAL", messages + [f"Missing required value: {canonical}"]
                    continue
                if _empty(value):
                    continue
                expected = rule.get("type", "string")
                if not _valid_type(str(value).strip(), expected):
                    level, messages = "CRITICAL", messages + [f"Invalid {expected} for {canonical}: {value}"]
                    continue
                if expected in {"integer", "float", "number"}:
                    numeric = float(value)
                    if "min" in rule and numeric < rule["min"] or "max" in rule and numeric > rule["max"]:
                        level, messages = "CRITICAL", messages + [f"{canonical} outside {rule.get('min')}-{rule.get('max')}: {value}"]
                allowed = rule.get("allowed_values")
                if allowed and str(value).strip() not in {str(v) for v in allowed}:
                    level, messages = "CRITICAL", messages + [f"Invalid category for {canonical}: {value}"]
                if expected == "category" and re.fullmatch(r"[\d.\-]+", str(value).strip()):
                    if level != "CRITICAL": level = "WARNING"
                    messages.append(f"Numeric-looking value in categorical field {canonical}: {value}")
            if index in duplicate_indices and level != "CRITICAL":
                level = "WARNING"
                messages.append("Duplicate row detected")
            if constant_grade and level == "OK":
                level = "WARNING"
                messages.append("Constant embryo_grade across file")
            result = {"row_index": index + 2, "level": level, "messages": messages}
            results.append(result)
            annotated = {**row, "validation_messages": "; ".join(messages)}
            if level == "CRITICAL": rejected.append(annotated)
            else:
                accepted.append(row)
                if level == "WARNING": flagged.append(annotated)

        key_source = resolved[self.schema["primary_key"]]
        missing_key_ratio = sum(_empty(row.get(key_source)) for row in rows) / len(rows) if rows else 1.0
        if missing_key_ratio > 0.5:
            return self._quarantine(content, metadata, "More than 50% of rows lack the primary identifier")
        key_values = [str(row.get(key_source, "")).strip() for row in rows if not _empty(row.get(key_source))]
        duplicate_key_rows = len(key_values) - len(set(key_values))
        if key_values and duplicate_key_rows / len(key_values) > 0.5:
            return self._quarantine(content, metadata, "Duplicate primary identifiers affect more than 50% of rows")
        clean_path = self.root / "processed" / f"{metadata['intake_id']}_clean.csv"
        self._write_csv(clean_path, headers, accepted)
        self._merge_clean_master(headers, accepted)
        if rejected: self._write_csv(self.root / "staging" / "quarantined" / f"{metadata['intake_id']}_rejected_rows.csv", headers + ["validation_messages"], rejected)
        if flagged: self._write_csv(self.root / "staging" / "flagged" / f"{metadata['intake_id']}_flagged_rows.csv", headers + ["validation_messages"], flagged)
        summary = {"status": "ACCEPTED", "original_row_count": len(rows), "clean_rows": len(rows) - len(rejected) - len(flagged), "accepted_rows": len(accepted), "warning_rows": len(flagged), "critical_rows": len(rejected), "duplicate_rows": len(duplicate_indices)}
        self._write_reports(metadata, summary, results)
        return IntakeResult(metadata, summary, clean_path)

    @staticmethod
    def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
            writer.writeheader(); writer.writerows(rows)

    def _merge_clean_master(self, incoming_headers: list[str], incoming_rows: list[dict[str, Any]]) -> None:
        master = self.root / "processed" / "clean_master_dataset.csv"
        existing_rows: list[dict[str, Any]] = []
        headers = list(incoming_headers)
        if master.exists():
            with master.open(encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                existing_rows = list(reader)
                headers = list(dict.fromkeys(list(reader.fieldnames or []) + headers))
        combined, seen = [], set()
        for row in existing_rows + incoming_rows:
            normalized = {header: row.get(header, "") for header in headers}
            fingerprint = tuple(normalized.items())
            if fingerprint not in seen:
                combined.append(normalized)
                seen.add(fingerprint)
        self._write_csv(master, headers, combined)

    def _write_reports(self, metadata: dict[str, Any], summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        report = {"metadata": metadata, "summary": summary, "row_results": rows}
        (self.root / "reports" / f"{metadata['intake_id']}_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        html_rows = "".join(f"<tr><td>{r['row_index']}</td><td>{html.escape(r['level'])}</td><td>{html.escape('; '.join(r['messages']))}</td></tr>" for r in rows)
        (self.root / "reports" / f"{metadata['intake_id']}_validation.html").write_text(f"<!doctype html><meta charset='utf-8'><title>Validation report</title><h1>{html.escape(metadata['file_name'])}</h1><pre>{html.escape(json.dumps(summary, indent=2))}</pre><table><tr><th>Row</th><th>Level</th><th>Messages</th></tr>{html_rows}</table>", encoding="utf-8")
        ledger = self.root / "reports" / "ingestion_report.csv"
        exists = ledger.exists()
        with ledger.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["intake_id", "upload_timestamp", "file_name", "checksum", "status", "row_count", "accepted_rows", "warning_rows", "critical_rows"])
            if not exists: writer.writeheader()
            writer.writerow({"intake_id": metadata["intake_id"], "upload_timestamp": metadata["upload_timestamp"], "file_name": metadata["file_name"], "checksum": metadata["checksum"], "status": summary["status"], "row_count": metadata.get("row_count"), "accepted_rows": summary.get("accepted_rows", 0), "warning_rows": summary.get("warning_rows", 0), "critical_rows": summary.get("critical_rows", 0)})
        notification = {
            "event": "ovulite.data_intake.completed",
            "severity": "error" if summary["status"] == "QUARANTINED" else "warning" if summary.get("warning_rows", 0) else "info",
            "intake_id": metadata["intake_id"], "file_name": metadata["file_name"],
            "status": summary["status"], "summary": summary,
            "message": f"Ovulite intake {summary['status']}: {metadata['file_name']}",
        }
        (self.root / "reports" / "notifications" / f"{metadata['intake_id']}.json").write_text(json.dumps(notification, indent=2), encoding="utf-8")
