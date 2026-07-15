import csv
import io
import zipfile

from app.services.data_intake import DataIntakeService


HEADER = ["# ET", "ET Date", "Recipient ID", "Embryo Stage 4-8", "Embryo Grade", "CL Side", "1st PC Result", "2nd PC Result", "Fetal Sexing"]


def csv_bytes(rows):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(HEADER)
    writer.writerows(rows)
    return stream.getvalue().encode()


def service(tmp_path):
    return DataIntakeService(data_root=tmp_path)


def test_valid_csv_is_preserved_validated_and_reported(tmp_path):
    result = service(tmp_path).process(
        "ET_Data.csv",
        csv_bytes([[1, "2025-05-01", "R-1", 7, 1, "Left", "Pregnant", "", "Female"]]),
        uploaded_by="tester",
    )
    assert not result.quarantined
    assert result.summary["accepted_rows"] == 1
    assert result.metadata["checksum"]
    assert result.clean_csv_path.exists()
    assert (tmp_path / result.metadata["raw_path"]).exists()
    assert (tmp_path / "reports" / f"{result.metadata['intake_id']}_summary.json").exists()


def test_critical_rows_are_separated_from_clean_output(tmp_path):
    result = service(tmp_path).process(
        "ET_Data.csv",
        csv_bytes([
            [1, "2025-05-01", "R-1", 7, 1, "Left", "Pregnant", "", "Female"],
            [2, "not-a-date", "R-2", 12, 1, "Middle", "Maybe", "9", "22"],
        ]),
    )
    assert result.summary["critical_rows"] == 1
    assert result.summary["accepted_rows"] == 1
    rejected = list((tmp_path / "staging" / "quarantined").glob("*_rejected_rows.csv"))
    assert len(rejected) == 1


def test_new_records_file_is_quarantined_without_parsing(tmp_path):
    result = service(tmp_path).process("New_Records_ET_Data.csv", b"broken,data\n")
    assert result.quarantined
    assert result.summary["status"] == "QUARANTINED"
    assert "policy" in result.summary["reason"]


def test_image_zip_is_integrity_checked_and_extracted(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("images/blastocyst-1.jpg", b"fake-image-content")
    result = service(tmp_path).process("Blastocyst_images.zip", buffer.getvalue())
    assert not result.quarantined
    assert result.summary == {"status": "IMAGE_ACCEPTED", "image_count": 1, "clean_rows": 0, "warning_rows": 0, "critical_rows": 0}


def test_zip_path_traversal_is_quarantined(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.jpg", b"bad")
    result = service(tmp_path).process("Blastocyst_images.zip", buffer.getvalue())
    assert result.quarantined
    assert "unsafe" in result.summary["reason"]
