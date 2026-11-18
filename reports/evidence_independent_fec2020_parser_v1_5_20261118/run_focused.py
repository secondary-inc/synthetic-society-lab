from pathlib import Path
import sys,resource,signal,time,json,unittest,sysconfig,os
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(120)
root=Path.cwd();sys.path.insert(0,str(root/'src'));start=time.monotonic()
from civiclab.e01 import fec2020_parser_v1
stdlib=Path(sysconfig.get_path('stdlib')).resolve();tests=root/'tests/test_fec2020_parser_v1.py';extra=root/'reports/evidence_independent_fec2020_parser_v1_2_20261118/additional_controls.py';contract=root/'configs/e01_fec2020_senate_mapping_v1.json'
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.fork','os.posix_spawn','os.system','sqlite3.connect','ctypes.dlopen'):raise RuntimeError('NO_NETWORK_PROCESS_OWNER')
 if event=='open' and not isinstance(args[0],int):
  p=Path(args[0]).resolve();flags=args[2]
  assert not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
  assert p in (tests,extra,contract) or p.is_relative_to(stdlib)
sys.addaudithook(audit);suite=unittest.TestSuite()
for path in (tests,extra):
 import types
 mod=types.ModuleType('_independent_'+path.stem);mod.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),mod.__dict__);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
class IndependentSeparatorControls(unittest.TestCase):
 def row(self):
  vals=[None]*26;vals[0]=2;vals[1]='IA';vals[2]='AUTHORED_STATE';vals[4]='n/a'
  return [fec2020_parser_v1.Cell(v,'s' if type(v) is str else 'n') for v in vals]
 def test_each_other_column_data_refused(self):
  for col in set(range(26))-{0,1,2,4}:
   for value in (0,'',False):
    cells=self.row();cells[col]=fec2020_parser_v1.Cell(value,'s' if type(value) is str else 'b' if type(value) is bool else 'n')
    with self.subTest(col=col,value=value),self.assertRaises(fec2020_parser_v1.ParserRefused):fec2020_parser_v1.row_record(cells,2,{})
 def test_none_fec_retains_raw_provenance(self):
  cells=self.row();cells[4]=fec2020_parser_v1.Cell(None,'n');r=fec2020_parser_v1.row_record(cells,2,{'source':'AUTHORED'})
  self.assertEqual(r['role'],'STATE_ONLY_SEPARATOR');self.assertEqual(r['raw_row']['values'][2],'AUTHORED_STATE');self.assertEqual(r['source'],{'source':'AUTHORED'});self.assertEqual(r['stages'],[]);self.assertFalse(r['candidate_identity_accepted'])
 def test_invalid_ordinal_not_separated(self):
  for value in (True,1,'2'):
   cells=self.row();cells[0]=fec2020_parser_v1.Cell(value,'s' if type(value) is str else 'b' if type(value) is bool else 'n')
   with self.subTest(value=value),self.assertRaises(fec2020_parser_v1.ParserRefused):fec2020_parser_v1.row_record(cells,2,{})
 def test_blank_or_nonliteral_fec_refused(self):
  for value in ('','N/A','n/a ','AUTHORED_FEC',False,0):
   cells=self.row();cells[4]=fec2020_parser_v1.Cell(value,'s' if type(value) is str else 'b' if type(value) is bool else 'n')
   with self.subTest(value=value),self.assertRaises(fec2020_parser_v1.ParserRefused):fec2020_parser_v1.row_record(cells,2,{})
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentSeparatorControls))
r=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'kind':'INDEPENDENT_FEC_V1_5_FOCUSED','tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'successful':r.wasSuccessful(),'runtime':sys.version.split()[0],'CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'wall_seconds':time.monotonic()-start,'actual_workbook_reader_network_key_owner_calls':0},sort_keys=True));signal.alarm(0);raise SystemExit(0 if r.wasSuccessful() else 1)
