import importlib.util, tempfile, pathlib, hashlib, json, io, contextlib
from unittest.mock import patch
p=pathlib.Path('scripts/diagnose_openrouter_key_once_20261116.py')
s=importlib.util.spec_from_file_location('candidate',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
checks=[]
def ok(name, cond):
 assert cond,name
 checks.append(name)
secret='MOCK_SENTINEL_CREDENTIAL'
class Credential: _value=secret
class Response:
 def __init__(self,status=200,body=None,encoding='identity',ctype='application/json'):
  self.status=status; self.body=body if body is not None else json.dumps({'data':{'limit':1,'limit_remaining':0,'usage':1,'is_free_tier':False,'label':secret}}).encode(); self.encoding=encoding; self.ctype=ctype
 def getheader(self,k,d=None): return {'Content-Encoding':self.encoding,'Content-Type':self.ctype}.get(k,d)
 def read(self,n): return self.body[:n]
for label,r in [('ok',Response()),('402',Response(402)),('redirect',Response(302)),('large',Response(body=b'x'*65537)),('encoding',Response(encoding='gzip')),('schema',Response(body=b'[]'))]:
 with tempfile.TemporaryDirectory() as td:
  base=pathlib.Path(td)/'once'; reader=pathlib.Path(td)/'reader.py'; reader.write_text('# mock only\n'); calls=[]
  class Connection:
   def __init__(self,host,**kw): ok(label+' fixed TLS host',host=='openrouter.ai' and kw['timeout']==15 and kw['context'] is not None)
   def request(self,method,path,headers): calls.append((method,path)); ok(label+' credential sent only as authorization',headers['Authorization']=='Bearer '+secret)
   def getresponse(self): return r
   def close(self): pass
  with patch.object(m,'BASE',base),patch.object(m,'READER',reader),patch.object(m,'READER_SHA',hashlib.sha256(reader.read_bytes()).hexdigest()),patch.object(m.runpy,'run_path',return_value={'_credential':lambda root:Credential()}),patch.object(m.http.client,'HTTPSConnection',Connection),patch.object(m.signal,'signal'),patch.object(m.signal,'alarm'):
   with contextlib.redirect_stdout(io.StringIO()) as out: m.main()
   result=json.loads((base/'result.json').read_text())
   ok(label+' one GET only',calls==[('GET','/api/v1/key')]);ok(label+' safe retention',secret not in out.getvalue() and all(secret not in f.read_text() for f in base.iterdir()))
   ok(label+' correct terminal',result['status']==('READONLY_STATUS_OBSERVED' if label=='ok' else 'STOPPED'))
   try: m.main();raise AssertionError('replay admitted')
   except FileExistsError: pass
   ok(label+' replay denied',len(calls)==1)
for value in [True,'0',float('nan'),float('inf'),{},[]]:
 try: m.safe_projection({'data':{'usage':value}});raise AssertionError('bad numeric accepted')
 except ValueError: pass
 ok('reject numeric '+repr(value),True)
ok('null valid',m.safe_projection({'data':{'limit':None}})=={'limit':None})
ok('identity stripped',m.safe_projection({'data':{'label':secret,'hash':secret,'budgets':[{'scope':'api_key','id':secret,'remaining_usd':0}]}})=={'budgets':[{'scope':'api_key','remaining_usd':0}]})
print(json.dumps({'checks':len(checks),'passed':checks,'candidate_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
