"""Fixed authored backend process; no PDF library, plugin, source paths or network."""
import base64
import json
import resource
import sys
from civiclab.e01.clerk2020_contracts_v1 import canonical,require
from civiclab.e01.clerk2020_inspection_m1_v1 import policy_from_bytes,project_authored,strict_json


def main():
    # Import required trusted code first; prohibit external I/O during projection.
    def guard(event,args):
        if event in {'open','os.listdir','os.scandir','os.system','subprocess.Popen','os.fork','ctypes.dlopen'} or event.startswith('socket.') or event.startswith('os.exec'):
            raise PermissionError('AUTHORED_BACKEND_IO_REFUSED')
    sys.addaudithook(guard)
    raw=sys.stdin.buffer.read(4194305);require(len(raw)<=4194304)
    packet=json.loads(raw);require(type(packet) is dict and set(packet)=={'policy_b64','documents_b64'})
    cfg=policy_from_bytes(base64.b64decode(packet['policy_b64'],validate=True));limits=cfg['limits']
    resource.setrlimit(resource.RLIMIT_CPU,(limits['cpu_soft_seconds'],limits['cpu_hard_seconds']))
    def rss():
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak=int(value) if sys.platform=='darwin' else int(value)*1024
        require(0<peak<=limits['rss_peak_bytes']);return peak
    rss();require(type(packet['documents_b64']) is list and 1<=len(packet['documents_b64'])<=limits['documents'])
    documents=[base64.b64decode(x,validate=True) for x in packet['documents_b64']]
    projection=project_authored(documents,cfg)
    response={'projection':projection,'resources':{'rss_peak_bytes':rss(),'cpu_limit_applied':True,'rss_checks_applied':True,
      'cpu_soft_seconds':limits['cpu_soft_seconds'],'cpu_hard_seconds':limits['cpu_hard_seconds'],
      'rss_semantics':'TRUSTED_CHILD_GETRUSAGE_PEAK_NOT_CONTINUOUS_HARD_RSS','rss_backend':cfg['rss_backend']}}
    encoded=canonical(response);require(len(encoded)<=limits['output_bytes'])
    sys.stdout.buffer.write(encoded);sys.stdout.buffer.flush()

if __name__=='__main__':
    try:main()
    except BaseException:sys.exit(2)
