import csv
import io
import zipfile
from .common import sha256_file


def ingest(path, expected_sha256):
    if sha256_file(path) != expected_sha256:
        raise ValueError("GDELT checksum mismatch")
    records = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != 1 or not names[0].endswith('.gkg.csv') or archive.testzip():
            raise ValueError("unexpected GKG archive")
        with archive.open(names[0]) as stream:
            for line, row in enumerate(csv.reader(io.TextIOWrapper(stream, encoding='utf-8-sig'), delimiter='\t'), 1):
                if len(row) != 27:
                    raise ValueError(f"expected 27 fields at row {line}")
                records.append({"record_id": row[0], "processing_batch_utc": row[1],
                                "source": row[3], "url": row[4], "published_at_utc": None,
                                "reuse_status": "UNVERIFIED", "forecast_admissible": False})
    return {"kind": "INGESTION_FIXTURE", "records": records,
            "source_sha256": expected_sha256, "not_news_text": True}
