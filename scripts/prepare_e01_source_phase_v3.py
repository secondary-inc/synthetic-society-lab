"""One-shot bounded technical metadata delivery. No campaign issue/execution."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from civiclab.e01 import clerk2020_source_job_v2 as j

READ_CAP=1048576
READ_COUNTS={'BOOT':2,'EXEC':6}
TECH_BASE='data/processed/e01_clerk2020_source_packet_preparation_v3'
WRITE_CAP=196608


class TechnicalReads:
    def __init__(self,root,phase,allowed):
        self.allowed=frozenset(allowed)
        self.root=root;self.phase=phase;self.reserved=0;self.observed=0;self.records=[]
    def read(self,path,maximum):
        path=path.absolute();j.n.no_alias(path)
        j.require(path in self.allowed and path.is_relative_to(self.root) and not path.is_relative_to(self.root/'data/raw')
                  and '.env' not in path.parts and maximum>0)
        size=path.stat().st_size
        j.require(size+1<=maximum and len(self.records)<READ_COUNTS[self.phase]
                  and self.reserved+size+1<=READ_CAP)
        self.reserved+=size+1
        record={'path':str(path.relative_to(self.root)),'reserved_bytes':size+1,
                'observed_bytes':None,'sha256':None}
        self.records.append(record)
        body,charge=j.read_file(path,size+1)
        j.require(charge==size+1);self.observed+=len(body)
        record.update(observed_bytes=len(body),sha256=j.sha(body))
        return body,{'path':record['path'],'bytes':len(body),'sha256':record['sha256']}


def prepare(root,phase,review_path,out,boot_packet=None):
    root=root.absolute();review_path=review_path.absolute();out=out.absolute()
    if boot_packet is not None:
        boot_packet=boot_packet.absolute();j.n.no_alias(boot_packet)
        j.require(boot_packet.is_relative_to(root/'data/processed') and boot_packet.name.endswith('.local.json'))
    j.n.no_alias(root);j.n.no_alias(review_path);j.n.no_alias(out)
    j.require(phase in READ_COUNTS and review_path.is_relative_to(root/'reports')
              and out.is_relative_to(root/'data/processed') and (phase=='BOOT' or boot_packet is not None))
    scope=root/TECH_BASE/phase
    j.n.no_alias(scope);scope.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    scope.mkdir(mode=0o700,exist_ok=False);j.n.fsync_dir(scope.parent)
    written=[0]
    def write(path,body):
        j.require(type(body) is bytes and written[0]+len(body)<=WRITE_CAP)
        written[0]+=len(body)
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);j.n.no_alias(path)
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            j.require(stream.write(body)==len(body));stream.flush();os.fsync(stream.fileno())
        j.n.fsync_dir(path.parent)
    write(scope/'STARTED.local.json',j.canonical({'kind':'TECHNICAL_SOURCE_PACKET_PREPARATION_V3',
        'phase':phase,'read_bytes_ceiling':READ_CAP,'read_count_ceiling':READ_COUNTS[phase],
        'write_bytes_ceiling':WRITE_CAP,'source_reads':0,'runtime_binary_reads':0,
        'campaign_issue_or_execution':False,'no_retry':True,'root_sha256':j.sha(str(root).encode())}))
    registry=j.n.FixedRegistrar(j.n.FixedStore(root),j.source_set_sha())
    allowed={review_path,root/j.METHODS} if phase=='BOOT' else {review_path,boot_packet,
        *(registry.store.path(slot) for slot in ('prepared_metadata','source_index','anchor_initial','anchor_boot'))}
    reader=TechnicalReads(root,phase,allowed);status='FAILED_UNKNOWN_NO_RETRY';result=None
    try:
        review_raw,review_ref=reader.read(review_path,131073)
        review=j.metadata_json(review_raw,131072)
        if phase=='BOOT':
            methods_raw,methods_ref=reader.read(root/j.METHODS,65537)
            j.require(j.sha(methods_raw)==j.METHODS_SHA)
            methods=j.metadata_json(methods_raw,65536)
            # Use exact independent frozen references, never preflight code.
            codes=review['code_refs'];j.exact(codes,j.CODE_PATHS)
            spec={'kind':'CLERK_SOURCE_STATIC_SPEC_V2_1','root_sha256':j.sha(str(root).encode()),
                'source_set_sha256':j.source_set_sha(),'methods_ref':methods_ref,'code_refs':codes,
                'qualified_ref':methods['qualified_worker'],'runtime_review_ref':methods['qualified_runtime_actual'],
                'acquisition_refs':[methods['accepted_acquisition'],methods['acquisition_handoff']],
                'ancestor_refs':methods['past_consumed_qualification_records'],
                'past_limits':methods['past_qualified_limits'],'code_review_ref':review_ref}
            j.check_code_review(review,spec);anchor=None
            decision={'kind':'CLERK_SOURCE_DECISION_V2_1','phase':phase,'static_spec_sha256':j.digest(spec),
                'source_set_sha256':j.source_set_sha(),'phase_budget':j.n.PREFIX_BUDGETS[phase],
                'expected_anchor_sha256':None}
        else:
            boot_raw,_=reader.read(boot_packet,129025)
            boot,_=j.phase_packet(root,boot_raw,j.sha(boot_raw),'BOOT');spec=boot['static_spec']
            store=registry.store;j.require(not store.exists('private_stderr'))
            prepared_raw,_=reader.read(store.path('prepared_metadata'),2049)
            prepared=j.decode(prepared_raw,2048)
            pref={'slot':'prepared_metadata','bytes':len(prepared_raw),'sha256':j.sha(prepared_raw)}
            index_raw,_=reader.read(store.path('source_index'),2049)
            j.require(j.canonical(j.decode(index_raw))==j.canonical(registry.binding()))
            a0_raw,_=reader.read(store.path('anchor_initial'),1537)
            a1_raw,_=reader.read(store.path('anchor_boot'),2049)
            a0=j.decode(a0_raw,2048);a1=j.decode(a1_raw,2048);anchor=j.sha(a1_raw)
            j.require(a0['kind']==a1['kind']=='CLERK_SOURCE_ANCHOR_V2_1'
                and a0['binding']==a1['binding']==registry.binding()
                and a0['state']=='anchor_initial' and a1['state']=='anchor_boot'
                and a0['previous_anchor_sha256'] is None and a1['previous_anchor_sha256']==j.sha(a0_raw)
                and prepared['binding']==registry.binding()
                and prepared['completed_bootstrap_anchor_sha256']==anchor)
            j.require(review.get('status')=='PASS_PREPARED_EXACT_SOURCE_FORMAT_JOB'
                and review.get('reviewer_role')=='independent_auditor'
                and review.get('prepared_sha256')==pref['sha256']
                and review.get('source_set_sha256')==j.source_set_sha()
                and review.get('source_authority')=='EXACT_TWO_SOURCES_FORMAT_ONLY')
            decision={'kind':'CLERK_SOURCE_DECISION_V2_1','phase':phase,'static_spec_sha256':j.digest(spec),
                'source_set_sha256':j.source_set_sha(),'phase_budget':j.n.PREFIX_BUDGETS[phase],
                'expected_anchor_sha256':anchor,'prepared_ref':pref,
                'prepared_review_ref':review_ref,'job_id':j.JOB}
        if phase=='EXEC':
            registry.store.bind_run(j.run_id(j.n.CAMPAIGN,j.JOB,decision))
            j.require(not any(registry.store.exists(slot) for slot in
                ('exec_issued','anchor_active','anchor_complete','anchor_invalid')))
        issued={'kind':'CLERK_SOURCE_ISSUED_V2_1','phase':phase,'ordinal':1,'binding':registry.binding(),
            'decision_sha256':j.digest(decision),'expected_anchor_sha256':anchor,'one_shot':True,
            'prefix_budget':j.n.PREFIX_BUDGETS[phase]}
        packet=j.canonical({'kind':'CLERK_SOURCE_PHASE_PACKET_V2_1','registration':registry.binding(),
                           'static_spec':spec,'decision':decision,'issued':issued})
        j.phase_packet(root,packet,j.sha(packet),phase)
        write(out,packet);status='PREPARED_NOT_EXECUTED'
        result={'kind':status,'phase':phase,'path':str(out),'bytes':len(packet),
                'sha256':j.sha(packet),'source_reads':0,'registrar_issued':False,'model_calls':0}
        return result
    finally:
        receipt={'kind':'TECHNICAL_SOURCE_PACKET_PREPARATION_RECEIPT_V3','status':status,'phase':phase,
            'read_count':len(reader.records),'reserved_read_bytes':reader.reserved,
            'observed_read_bytes':reader.observed,'reads':reader.records,'packet':result,
            'source_reads':0,'runtime_binary_reads':0,'campaign_issue_or_execution':False,
            'credit_restored':0,'no_retry':True}
        write(scope/'RECEIPT.local.json',j.canonical(receipt))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['BOOT','EXEC']);p.add_argument('--review',required=True)
    p.add_argument('--out',required=True);p.add_argument('--boot-packet')
    args=p.parse_args();root=Path.cwd()
    result=prepare(root,args.phase,root/args.review,root/args.out,
                   None if args.boot_packet is None else root/args.boot_packet)
    print(json.dumps(result,sort_keys=True))
