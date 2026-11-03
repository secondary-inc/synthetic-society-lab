import argparse
import json
from pathlib import Path
from .integrity import validate_sources
from .gates import MODULES
from .common import atomic_json


def main():
    parser = argparse.ArgumentParser(prog="civiclab")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    integrity = commands.add_parser("validate-sources")
    integrity.add_argument("--fixture-only", action="store_true")
    integrity.add_argument("--out", type=Path)
    commands.add_parser("modules")
    gdelt = commands.add_parser('gdelt-ingest')
    gdelt.add_argument('--out', type=Path, default=Path('data/processed/gdelt/fixture.json'))
    commands.add_parser('e02-fit')
    pilot = commands.add_parser('e02-pilot')
    pilot.add_argument('--population', type=Path, required=True, help='population.json from a recorded fit')
    pilot.add_argument('--seed', type=int, default=20261103)
    pilot.add_argument('--profiles', type=int, default=12)
    pilot.add_argument('--repeats', type=int, default=1)
    pilot.add_argument('--resume', type=Path)
    commands.add_parser('e01-demo')
    commands.add_parser('e01-audit')
    dashboard=commands.add_parser('dashboard')
    dashboard.add_argument('--out',type=Path,default=Path('data/processed/dashboard'))
    dashboard.add_argument('--run',action='append',dest='runs',help='Select a recorded run ID; repeat to include more')
    server=commands.add_parser('serve')
    server.add_argument('--directory',type=Path,default=Path('data/processed/dashboard'))
    server.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    if args.command == "modules":
        print(json.dumps(MODULES, indent=2))
        return
    if args.command == 'gdelt-ingest':
        from .gdelt import ingest
        manifest = json.loads((args.root / 'tests/fixtures/gdelt/manifest.json').read_text())
        result = ingest(args.root / manifest['path'], manifest['sha256'])
        atomic_json(args.root / args.out, result)
        print(json.dumps({'status':'PASS_FIXTURE', 'records':len(result['records']), 'out':str(args.out)}))
        return
    if args.command == 'dashboard':
        from .dashboard import build
        print(build(args.root,args.root/args.out,args.runs))
        return
    if args.command == 'serve':
        from .dashboard import serve
        serve(args.root/args.directory,args.port)
        return
    if args.command == 'e02-fit':
        from .e02.experiment import run_population
        print(run_population(args.root))
        return
    if args.command == 'e02-pilot':
        from .e02.experiment import run_pilot
        population = json.loads(args.population.read_text())
        print(run_pilot(args.root, population, seed=args.seed, n=args.profiles, repeats=args.repeats, resume=args.resume))
        return
    if args.command in ('e01-demo', 'e01-audit'):
        from .e01 import run_demo, run_audit
        print(run_demo(args.root) if args.command == 'e01-demo' else run_audit(args.root,args.root))
        return
    result = validate_sources(args.root, args.fixture_only)
    if args.out:
        atomic_json(args.out, result)
    print(json.dumps({"status": result["status"], "checks": len(result["checks"])}))
    if result["status"] != "PASS":
        raise SystemExit(2)
