"""Prepare a private authority packet from exact independent review metadata.

This does not issue a registrar slot, run BOOT/EXEC, read runtime binaries or open
an acquired source. Invoke the separately reviewed controller only as lead.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from civiclab.e01 import clerk2020_source_job_v1 as j


def ref(root,path):
    relative=str(path.relative_to(root))
    j.require(j.safe_relative(relative) and not relative.startswith(('data/raw/','.env')))
    body=path.read_bytes()
    return {'path':relative,'bytes':len(body),'sha256':j.sha(body)}


def prepare(root,phase,review_path,out,boot_packet=None):
    root=root.resolve();review_path=review_path.resolve();out=out.absolute()
    j.n.no_alias(root);j.n.no_alias(review_path);j.n.no_alias(out)
    j.require(review_path.is_relative_to(root/'reports') and out.is_relative_to(root/'data/processed'))
    review=j.metadata_json(review_path.read_bytes(),131072)
    registry=j.n.FixedRegistrar(j.n.FixedStore(root),j.source_set_sha())
    if phase=='BOOT':
        methods=j.metadata_json((root/j.METHODS).read_bytes(),65536)
        j.require(j.sha((root/j.METHODS).read_bytes())==j.METHODS_SHA)
        codes={name:{key:value for key,value in ref(root,root/name).items() if key!='path'} for name in j.CODE_PATHS}
        spec={'kind':'CLERK_SOURCE_STATIC_SPEC_V1_2','root_sha256':j.sha(str(root).encode()),
            'source_set_sha256':j.source_set_sha(),'methods_ref':ref(root,root/j.METHODS),'code_refs':codes,
            'qualified_ref':methods['qualified_worker'],'runtime_review_ref':methods['qualified_runtime_actual'],
            'acquisition_refs':[methods['accepted_acquisition'],methods['acquisition_handoff']],
            'ancestor_refs':methods['past_consumed_qualification_records'],'past_limits':methods['past_qualified_limits'],
            'code_review_ref':ref(root,review_path)}
        j.check_code_review(review,spec)
        decision={'kind':'CLERK_SOURCE_DECISION_V1_2','phase':'BOOT','static_spec_sha256':j.digest(spec),
            'source_set_sha256':j.source_set_sha(),'phase_budget':j.n.PREFIX_BUDGETS['BOOT'],'expected_anchor_sha256':None}
    else:
        j.require(boot_packet is not None)
        boot=j.decode(boot_packet.read_bytes(),j.MAX_AUTHORITY);spec=boot['static_spec']
        store=registry.store
        j.require(not store.exists('private_stderr'))
        body,charge=store.read('prepared_metadata',2049)
        prepared=j.decode(body,2048);anchor=registry.current()[0]
        pref={'slot':'prepared_metadata','bytes':len(body),'sha256':j.sha(body)}
        j.require(review.get('status')=='PASS_PREPARED_EXACT_SOURCE_FORMAT_JOB'
            and review.get('reviewer_role')=='independent_auditor' and review.get('prepared_sha256')==pref['sha256']
            and review.get('source_set_sha256')==j.source_set_sha()
            and review.get('source_authority')=='EXACT_TWO_SOURCES_FORMAT_ONLY'
            and prepared['completed_bootstrap_anchor_sha256']==anchor)
        decision={'kind':'CLERK_SOURCE_DECISION_V1_2','phase':'EXEC','static_spec_sha256':j.digest(spec),
            'source_set_sha256':j.source_set_sha(),'phase_budget':j.n.PREFIX_BUDGETS['EXEC'],
            'expected_anchor_sha256':anchor,'prepared_ref':pref,'prepared_review_ref':ref(root,review_path),'job_id':j.JOB}
    issued={'kind':'CLERK_SOURCE_ISSUED_V1_2','phase':phase,'ordinal':1,'binding':registry.binding(),
        'decision_sha256':j.digest(decision),'expected_anchor_sha256':decision['expected_anchor_sha256'],
        'one_shot':True,'prefix_budget':j.n.PREFIX_BUDGETS[phase]}
    packet={'kind':'CLERK_SOURCE_PHASE_PACKET_V1_2','registration':registry.binding(),
            'static_spec':spec,'decision':decision,'issued':issued}
    body=j.canonical(packet);j.phase_packet(root,body,j.sha(body),phase)
    out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
    j.n.fsync_dir(out.parent)
    return {'kind':'PREPARED_NOT_EXECUTED','phase':phase,'path':str(out),'bytes':len(body),
            'sha256':j.sha(body),'source_reads':0,'registrar_issued':False,'model_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['BOOT','EXEC']);p.add_argument('--review',required=True)
    p.add_argument('--out',required=True);p.add_argument('--boot-packet')
    args=p.parse_args();root=Path.cwd()
    result=prepare(root,args.phase,root/args.review,root/args.out,
                   None if args.boot_packet is None else root/args.boot_packet)
    print(json.dumps(result,sort_keys=True))
