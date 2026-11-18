"""Scaled wall-alarm mechanism with authored owner/key/HTTP doubles only."""
from pathlib import Path
import sys,json,time,signal,importlib.util
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
root=Path.cwd();sys.path.insert(0,str(root/'src'));tracepath=Path(sys.argv[1])
def trace(value):
 with tracepath.open('a') as f:f.write(value+'\n');f.flush()
from civiclab.e02 import wrapper_crossmodel_slot46_v2_client as client
from civiclab.e02 import wrapper_crossmodel_slot46_v2 as p
from civiclab.common import canonical_hash
spec=importlib.util.spec_from_file_location('authored_wall_entry',root/'scripts/launch_e02_slot46_v2_20261118.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
original=RuntimeError('AUTHORED_PRIMARY')
class Journal:
 def write(self,name,value):trace(name)
 def close(self):trace('JOURNAL_CLOSE')
class Owner:
 def open_canary(self,*a):pass
 def intent(self,*a):pass
 def register_proofs(self,*a):pass
 def grant(self):return {'receipt':'a'*32,'request':{'execution_order':46,'pair_seed':p.SEED,'payload':{}},'context':{'payload_hash':canonical_hash({})}}
 def transition(self,*a,**kw):trace('TRANSITION_ENTERED');time.sleep(0.50)
 def canary_snapshot(self):trace('READBACK_AFTER_TIMEOUT');return {'branch':{'closed':True},'row':{'status':'UNCERTAIN'}}
 def close_canary(self,*a):trace('FALLBACK_AFTER_WALL_TIMEOUT');time.sleep(0.15)
class Phase:
 def __init__(self,*a):pass
 def gate(self,*a,**kw):pass
class Capability:
 def __init__(self,*a):pass
 def post(self):raise original
now=datetime.now(timezone.utc);packet={'run_id':'AUTHORED_WALL_ONLY','parent_key':'b'*64,'valid_from_utc':(now-timedelta(seconds=10)).isoformat(),'valid_until_utc':(now+timedelta(seconds=600)).isoformat(),'price_release':{r:{'terms':{'model':r},'interpretation':{}} for r in ('A','B')}}
native_setitimer=signal.setitimer
calls=[]
def scaled(which,seconds,*a):
 calls.append(seconds);trace('CONFIGURED_WALL='+str(seconds));return native_setitimer(which,0.15 if seconds else 0,*a)
t=time.monotonic();caught=None
with patch.object(client,'validate_release'),patch.object(client,'fresh_proof',return_value={}),patch.object(client,'_Phase',Phase),patch.object(client,'_Capability',Capability),patch.object(client,'_Journal',return_value=Journal()),patch.object(entry,'read_exact',side_effect=lambda path,*a:packet if path.name=='packet.json' else {}),patch.object(entry,'_make_owner',return_value=Owner()),patch.object(entry,'_credential',return_value=object()),patch.object(entry,'_make_transport',return_value=object()),patch.object(entry,'_catalog',side_effect=lambda _: (b'{}',{})),patch.object(entry.signal,'setitimer',side_effect=scaled),patch.object(sys,'argv',['authored','--packet-sha256','c'*64,'--release-sha256','d'*64]):
 try:entry.main()
 except BaseException as e:caught=e
print(json.dumps({'kind':'AUTHORED_SCALED_WALL_SMOKE','configured_main_timer_arguments':calls,'smoke_alarm_seconds':0.15,'elapsed_seconds':time.monotonic()-t,'original_error_preserved':caught is original,'trace':tracepath.read_text().splitlines(),'current_owner_calls':0,'actual_key_reads':0,'network_calls':0,'full_closed_owner_integration':False},sort_keys=True))
