import csv
import io
import zipfile
import json
import os
import tempfile
import hashlib
from pathlib import Path
from .common import sha256_file,atomic_json


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


def ingest_fixture(root,out=Path('data/processed/gdelt/fixture.json'),summary=None):
    """Publish immutable CSV bytes, then atomically replace their JSON pointer."""
    root=Path(root);manifest=json.loads((root/'tests/fixtures/gdelt/manifest.json').read_text())
    result=ingest(root/manifest['path'],manifest['sha256'])
    if len(result['records'])!=manifest['records']:
        raise ValueError('registered GKG record count mismatch')
    out=root/out;summary=root/summary if summary is not None else out.with_suffix('.csv')
    protected={(root/manifest['path']).resolve(),(root/'tests/fixtures/gdelt/manifest.json').resolve()}
    if out.resolve()==summary.resolve() or any(
        path.resolve() in protected or path.resolve().is_relative_to((root/'data/raw').resolve())
        for path in (out,summary)):
        raise ValueError('distinct derived outputs must not overwrite registered source inputs')
    fields=['record_id','processing_batch_utc','source','url','published_at_utc','reuse_status','forecast_admissible']
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields)
    writer.writeheader();writer.writerows(result['records'])
    digest=hashlib.sha256(stream.getvalue().encode()).hexdigest()
    if summary.exists() and sha256_file(summary)!=digest:
        raise FileExistsError('CSV summaries are immutable; choose a new output path')
    summary.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=summary.parent,prefix='.writing-')
    try:
        with os.fdopen(fd,'w',newline='') as target:
            target.write(stream.getvalue());target.flush();os.fsync(target.fileno())
        try:os.link(name,summary)  # Atomic creation; never clobber a prior CSV.
        except FileExistsError:
            if sha256_file(summary)!=digest:raise ValueError('concurrent CSV content differs')
    finally:
        if os.path.exists(name):os.unlink(name)
    summary_path=str(summary.resolve().relative_to(root.resolve())) if summary.resolve().is_relative_to(root.resolve()) else str(summary.resolve())
    result['csv_summary']={'path':summary_path,'sha256':sha256_file(summary),
                           'scope':'Metadata only; empty publication dates and forecast_admissible=False are intentional.'}
    atomic_json(out,result)
    return {'status':'PASS_FIXTURE','records':len(result['records']),'out':str(out),'summary':str(summary)}


def verify_fixture_export(root,out=Path('data/processed/gdelt/fixture.json')):
    """Consumers reject mixed/tampered summaries; the CSV is immutable via this API."""
    root=Path(root);data=json.loads((root/out).read_text());summary=root/data['csv_summary']['path']
    if sha256_file(summary)!=data['csv_summary']['sha256']:
        raise ValueError('CSV/JSON summary hash mismatch')
    with summary.open(newline='') as stream:rows=list(csv.DictReader(stream))
    if len(rows)!=len(data['records']):raise ValueError('CSV/JSON row count mismatch')
    for row,record in zip(rows,data['records']):
        if row!={key:'' if value is None else str(value) for key,value in record.items()}:
            raise ValueError('CSV/JSON content mismatch')
    return {'status':'PASS_EXPORT_PAIR','records':len(rows),'csv_sha256':sha256_file(summary)}
