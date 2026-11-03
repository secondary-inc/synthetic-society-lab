"""Compatibility entry point referenced by the original research blueprint."""
import argparse
import json
from pathlib import Path
from civiclab.gdelt import ingest_fixture


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out',type=Path,default=Path('data/processed/gdelt/fixture.json'))
    parser.add_argument('--summary',type=Path)
    args=parser.parse_args()
    print(json.dumps(ingest_fixture(args.root,args.out,args.summary)))
