"""Pinned credential-loader source on synthetic files and inert git only."""
from pathlib import Path
import sys,tempfile,importlib.util,hashlib,subprocess,json,os
from unittest.mock import patch
root=Path.cwd();sys.path.insert(0,str(root/'src'));spec=importlib.util.spec_from_file_location('authored_credential_entry',root/'scripts/launch_e02_slot46_v2_20261118.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
from civiclab.production_admission_v4 import _Credential
from civiclab.model import ExecutionBlocked
raw=(root/'scripts/collect_connectivity_billing_once.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==entry.KEY_READER_SHA
checks={}
with tempfile.TemporaryDirectory(prefix='AUTHORED_SLOT46_CREDENTIAL_') as tmp:
 base=Path(tmp).resolve();(base/'scripts').mkdir();script=base/'scripts/collect_connectivity_billing_once.py';script.write_bytes(raw);env=base/'.env';env.write_text('OPENROUTER_API_KEY='+'sk-or-v1-'+'AUTHORED_NOT_REAL_'*2+'\n');env.chmod(0o600);entry.ROOT=base;calls=[]
 def git(argv,**kw):
  assert argv==['git','-C',str(base),'check-ignore','--quiet','--','.env'] and kw=={'stdin':subprocess.DEVNULL,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL,'timeout':5};calls.append(1);return type('InertGit',(),{'returncode':0})()
 with patch.object(subprocess,'run',side_effect=git):value=entry._credential()
 checks['exact_loader_valid_synthetic_file']=type(value) is _Credential and len(calls)==1
 env.chmod(0o644)
 with patch.object(subprocess,'run',side_effect=git):
  try:entry._credential();checks['public_mode_refused']=False
  except ExecutionBlocked:checks['public_mode_refused']=True
 env.chmod(0o600)
 with patch.object(subprocess,'run',return_value=type('InertGit',(),{'returncode':1})()):
  try:entry._credential();checks['not_ignored_refused']=False
  except ExecutionBlocked:checks['not_ignored_refused']=True
 script.write_bytes(raw+b'\n')
 with patch.object(subprocess,'run') as call:
  try:entry._credential();checks['changed_loader_refused_before_git_or_credential']=False
  except RuntimeError:checks['changed_loader_refused_before_git_or_credential']=not call.called
assert all(checks.values());print(json.dumps({'kind':'INDEPENDENT_SYNTHETIC_KEY_LOADER_CONTROLS','runtime':sys.version.split()[0],'checks':checks,'actual_key_reads':0,'real_git_subprocesses':0,'network_calls':0,'credential_value_disclosed':False},sort_keys=True))
