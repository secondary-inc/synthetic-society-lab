"""Authored/inert download controls only; denies real networking/private reads."""
import contextlib,io,json,os,sys,resource,signal,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
resource.setrlimit(resource.RLIMIT_CPU,(899,900));signal.alarm(900);root=Path.cwd();t=time.monotonic();events={'network_attempts':0,'private_read_attempts':0,'denied_paths':[]}
def audit(event,args):
 if event.startswith(('socket.','ctypes.')) or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','os.exec'):
  events['network_attempts']+=1;raise PermissionError('EXTERNAL_DENIED')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(os.fsdecode(args[0])).absolute()
  if (p.is_relative_to(root/'data') and not p.is_relative_to(Path(sys.base_prefix).resolve())) or p.name=='.env':
   events['private_read_attempts']+=1;events['denied_paths'].append(str(p));raise PermissionError('PRIVATE_INPUT_DENIED')
sys.addaudithook(audit);sys.path[:0]=[str(root/'src'),str(root/'tests')]
import test_fec2020_download as old
source=old.source
class Independent(unittest.TestCase):
 setUp=old.FEC2020DownloadTests.setUp
 save=old.FEC2020DownloadTests.save
 def test_redirect_refusal_closes_response(self):
  fp=io.BytesIO(b'AUTHORED_REDIRECT_BODY')
  with self.assertRaisesRegex(source.SourceRefused,'REDIRECT_REFUSED'):source._NoRedirect().redirect_request(None,fp,302,None,{},source.URL)
  self.assertTrue(fp.closed,'Redirect response left open on refusal')
 def test_exclusive_publish_collision_preserves_existing_and_cleans_temp(self):
  path=self.root/source.RELATIVE_PATH
  def collide(src,dest):Path(dest).write_bytes(b'AUTHORED_EXISTING');raise FileExistsError()
  with patch.object(source.urllib.request,'build_opener') as factory,patch.object(source.os,'link',side_effect=collide):
   factory.return_value.open.return_value=old.Response(self.data)
   with self.assertRaises(FileExistsError):source.obtain(self.root,fetch=True)
  self.assertEqual(path.read_bytes(),b'AUTHORED_EXISTING');self.assertEqual([p.name for p in path.parent.iterdir()],[path.name])
 def test_fsync_failure_cleans_temp_and_publishes_nothing(self):
  with patch.object(source.urllib.request,'build_opener') as factory,patch.object(source.os,'fsync',side_effect=OSError('AUTHORED_FSYNC_FAILURE')):
   response=old.Response(self.data);factory.return_value.open.return_value=response
   with self.assertRaises(OSError):source.obtain(self.root,fetch=True)
  path=self.root/source.RELATIVE_PATH;self.assertFalse(path.exists());self.assertEqual(list(path.parent.iterdir()),[]);self.assertTrue(response.closed)
 def test_http_identity_refusal_closes_response_and_does_not_publish(self):
  response=old.Response(self.data);response.status=503
  with patch.object(source.urllib.request,'build_opener') as factory:
   factory.return_value.open.return_value=response
   with self.assertRaisesRegex(source.SourceRefused,'HTTP_IDENTITY_MISMATCH'):source.obtain(self.root,fetch=True)
  self.assertTrue(response.closed);self.assertFalse((self.root/source.RELATIVE_PATH).exists());factory.return_value.open.assert_called_once()
 def test_parent_escape_refused_before_fetch(self):
  with tempfile.TemporaryDirectory() as other:
   parent=(self.root/source.RELATIVE_PATH).parent;parent.parent.mkdir(parents=True);parent.symlink_to(other,target_is_directory=True)
   with patch.object(source.urllib.request,'build_opener') as factory:
    with self.assertRaisesRegex(source.SourceRefused,'UNSAFE_DESTINATION'):source.obtain(self.root,fetch=True)
   factory.assert_not_called();self.assertEqual(list(Path(other).iterdir()),[])
 def test_CLI_timer_installed_handler_used_and_restored(self):
  handlers=[];prior=object()
  def register(signum,handler):handlers.append(handler);return prior
  def expire(*args,**kwargs):handlers[0](signal.SIGALRM,None)
  output=io.StringIO()
  with patch.object(source.signal,'signal',side_effect=register),patch.object(source.signal,'alarm') as alarm,patch.object(source,'obtain',side_effect=expire),contextlib.redirect_stdout(output):
   status=source.main(['--root',str(self.root)])
  self.assertEqual(status,1);self.assertEqual(json.loads(output.getvalue())['error'],'WALL_LIMIT');self.assertEqual([c.args for c in alarm.call_args_list],[(60,),(0,)]);self.assertIs(handlers[-1],prior)
 def test_oversized_cache_never_fetches_or_mutates(self):
  path=self.save(self.data+b'X')
  with patch.object(source.urllib.request,'build_opener') as factory:
   with self.assertRaisesRegex(source.SourceRefused,'SIZE_MISMATCH'):source.obtain(self.root,fetch=True)
  factory.assert_not_called();self.assertEqual(path.read_bytes(),self.data+b'X')
 def test_unknown_exception_message_not_emitted(self):
  output=io.StringIO()
  with patch.object(source.signal,'signal'),patch.object(source.signal,'alarm'),patch.object(source,'obtain',side_effect=RuntimeError('AUTHORED_PRIVATE_SENTINEL')),contextlib.redirect_stdout(output):
   status=source.main(['--root',str(self.root)])
  self.assertEqual(status,1);self.assertEqual(json.loads(output.getvalue())['error'],'RuntimeError');self.assertNotIn('AUTHORED_PRIVATE_SENTINEL',output.getvalue())
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(old.FEC2020DownloadTests),unittest.defaultTestLoader.loadTestsFromTestCase(Independent)])
r=unittest.TextTestRunner(verbosity=1).run(suite);print('INDEPENDENT_FEC_DOWNLOAD='+json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'wall_seconds':time.monotonic()-t,**events},sort_keys=True));raise SystemExit(0 if r.wasSuccessful() else 1)
