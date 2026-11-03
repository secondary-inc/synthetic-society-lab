"""Local-only recorded-run viewer; no inference, data mutation or public hosting."""
from pathlib import Path
from importlib.resources import files
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .common import sha256_file, atomic_json, redact


def verified_run(path):
    path=Path(path).resolve()
    if not (path/'checksums.json').exists():
        raise ValueError('run incomplete: no artifact checksums')
    checks=json.loads((path/'checksums.json').read_text())
    if not {'manifest.json','summary.json','events.jsonl'} <= set(checks):
        raise ValueError('required run artifacts missing from checksum ledger')
    for name,digest in checks.items():
        target=(path/name).resolve()
        if not target.is_relative_to(path) or not target.is_file() or sha256_file(target)!=digest:
            raise ValueError('run artifact integrity failure: '+name)
    def read(name):
        if name not in checks:
            return None
        return json.loads((path/name).read_text())
    result={'manifest':read('manifest.json'),'summary':read('summary.json'),
            'run_directory':str(path),'checksums_sha256':sha256_file(path/'checksums.json'),
            'artifacts':checks,'integrity':'PASS'}
    for name,key in [('analysis.json','analysis'),('evaluation.json','evaluation'),
                     ('S0.evaluation.json','evaluation'),('S_ZERO.evaluation.json','simpler_evaluation'),
                     ('counterfactual.evaluation.json','counterfactual'),('paired_comparison.json','paired_comparison'),
                     ('returns_audit.json','returns_audit'),
                     ('population-support-comparison.json','population_comparison')]:
        if name in checks:result[key]=read(name)
    if 'population.json' in checks:
        pop=read('population.json')
        result['population']={k:pop[k] for k in ('diagnostics','source_hashes','confirmatory_status','mapping')}
    if 'citizen-targets.json' in checks:
        targets=read('citizen-targets.json')
        result['citizen_targets']={k:targets[k] for k in ('kind','dataset','included_state_dc_rows',
            'excluded_geographies','national_published25plus_sum','regional','targets','uncertainty',
            'scientific_population_gate','population_fit','provenance')}
    if 'responses.json' in checks:
        # Only fictional profiles and recorded responses; no donor records.
        result['replay']=[{k:r[k] for k in ('profile_id','stimulus_id','repeat','arm','pre','post','change','request_hashes')}
                          | {'exposure':r['post_request']['exposure']} for r in read('responses.json')]
    return redact(result)


def snapshot(root, run_ids=None):
    folder=Path(root)/'data/processed/runs'
    paths=[folder/name for name in run_ids] if run_ids else sorted(folder.glob('*'))
    runs=[]; rejected=[]
    for path in paths:
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError('run selection escapes store')
        try:
            runs.append(verified_run(path))
        except (ValueError,OSError,KeyError,json.JSONDecodeError) as error:
            rejected.append({'run_id':path.name,'reason':str(error)})
    from .orchestration import completion_status
    latest={}
    for run in sorted(runs,key=lambda r:r['manifest']['started_at_utc']):
        m=run['manifest'];latest[m['module']]=f"{m['kind']}: {run['summary']['status']}"
    result={'title':'Synthetic Society Lab','runs':runs,'rejected_runs':rejected,
            'scope':'Local recorded artifacts. MOCK is engineering data, not research findings. No human effects or prospective forecasts.',
            'modules':{'E01':latest.get('E01','No verified run in this snapshot'),'E02':latest.get('E02','No verified run in this snapshot'),
                       'E03':'DEFERRED','E04':'DEFERRED'},
            'privacy':'No credentials or respondent-level source data exported.'}
    if (Path(root)/'configs/completion_contract.json').exists():
        result['completion']=completion_status(root)
    return result


def build(root, output, run_ids=None):
    data=snapshot(root,run_ids)
    if not data['runs']:
        raise ValueError('no completed verified runs to display')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    atomic_json(output/'snapshot.json',data)
    template=files('civiclab').joinpath('templates/run-viewer.html').read_text()
    payload=json.dumps(data,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    (output/'index.html').write_text(template.replace('__RECORDED_DATA__',payload))
    return output/'index.html'


def serve(directory, port=8765):
    directory=Path(directory).resolve()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            name={'/':'index.html','/index.html':'index.html','/snapshot.json':'snapshot.json'}.get(self.path)
            if name is None:
                self.send_error(404);return
            path=directory/name
            if not path.is_file():
                self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8' if name.endswith('html') else 'application/json')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(path.read_bytes())
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Local: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
