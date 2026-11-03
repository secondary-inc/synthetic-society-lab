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
    costs=commands.add_parser('cost-plan')
    costs.add_argument('--spec',type=Path,required=True)
    costs.add_argument('--out',type=Path,default=Path('data/processed/planning/cost-plan.json'))
    restore=commands.add_parser('restore-inputs')
    restore.add_argument('--from',type=Path,required=True,dest='source_directory')
    restore.add_argument('--apply',action='store_true')
    completion=commands.add_parser('completion')
    completion.add_argument('--out',type=Path,default=Path('data/processed/orchestration/completion.json'))
    pack=commands.add_parser('repro-pack')
    pack.add_argument('--run',action='append',required=True,dest='runs')
    pack.add_argument('--out',type=Path,default=Path('data/processed/reproducibility/owner-review.zip'))
    gdelt = commands.add_parser('gdelt-ingest')
    gdelt.add_argument('--out', type=Path, default=Path('data/processed/gdelt/fixture.json'))
    commands.add_parser('e02-fit')
    commands.add_parser('e02-targets')
    stimuli=commands.add_parser('e02-stimuli')
    stimuli.add_argument('action',choices=['acquire','verify'],default='verify',nargs='?')
    pilot = commands.add_parser('e02-pilot')
    pilot.add_argument('--population', type=Path, required=True, help='population.json from a recorded fit')
    pilot.add_argument('--seed', type=int, default=20261103)
    pilot.add_argument('--profiles', type=int, default=12)
    pilot.add_argument('--repeats', type=int, default=1)
    pilot.add_argument('--resume', type=Path)
    commands.add_parser('e01-demo')
    commands.add_parser('e01-audit')
    historical=commands.add_parser('e01-historical')
    historical.add_argument('action',choices=['download','verify','prepare','run'])
    selection=commands.add_parser('e01-select-fixture')
    selection.add_argument('--fixture',type=Path,required=True)
    selection.add_argument('--max-seconds',type=float,default=60.)
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
    if args.command=='cost-plan':
        from .planning import cost_plan
        from .common import redact
        result=redact(cost_plan(json.loads((args.root/args.spec).read_text())))
        atomic_json(args.root/args.out,result)
        print(json.dumps({k:result[k] for k in ('status','call_count','total_reservation_usd','dispatch_authorized')}))
        return
    if args.command=='restore-inputs':
        from .intake import restore_inputs
        result=restore_inputs(args.root,args.source_directory,args.apply)
        print(json.dumps(result,indent=2))
        if result['status']=='BLOCKED':raise SystemExit(2)
        return
    if args.command=='completion':
        from .orchestration import write_completion
        result=write_completion(args.root,args.root/args.out)
        print(json.dumps({'status':result['status'],'passed':sum(r['status']=='PASS' for r in result['requirements']),
                          'required':len(result['requirements']),'out':str(args.out)}))
        return
    if args.command=='repro-pack':
        from .reproduction import build_package
        print(json.dumps(build_package(args.root,args.root/args.out,args.runs)))
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
    if args.command=='e02-targets':
        from .e02.citizen_targets import run_targets
        print(run_targets(args.root))
        return
    if args.command=='e02-stimuli':
        from .e02.stimuli import acquire,verify_corpus
        print(json.dumps(acquire(args.root) if args.action=='acquire' else verify_corpus(args.root),indent=2))
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
    if args.command=='e01-historical':
        from .e01.historical import download_sources,verify_sources,prepare,run_historical
        if args.action=='run':print(run_historical(args.root))
        elif args.action=='download':print(json.dumps(download_sources(args.root),indent=2))
        elif args.action=='verify':print(json.dumps(verify_sources(args.root),indent=2))
        else:
            result=prepare(args.root)
            atomic_json(args.root/'data/processed/e01/prepared_historical.json',result)
            print(json.dumps({'eligible':len(result['features']),'excluded':result['exclusions']}))
        return
    if args.command=='e01-select-fixture':
        from .e01.selection import run_fixture
        frame=json.loads((args.root/args.fixture).read_text())
        print(run_fixture(args.root,frame,max_seconds=args.max_seconds))
        return
    result = validate_sources(args.root, args.fixture_only)
    if args.out:
        atomic_json(args.out, result)
    print(json.dumps({"status": result["status"], "checks": len(result["checks"])}))
    if result["status"] != "PASS":
        raise SystemExit(2)
