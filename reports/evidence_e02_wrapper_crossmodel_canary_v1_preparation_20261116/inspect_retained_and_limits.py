"""Read-only closed evidence/AST preflight. No imports of project executors,
financial-owner instances, credential readers or network/model clients.
"""
from pathlib import Path
from datetime import datetime,timezone
import ast
import hashlib
import json
import resource
import signal

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
BASE=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01'
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
def deadline(*_):raise RuntimeError('OFFLINE_PREFLIGHT_90_SECOND_CAP')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,90)
READ_LIMIT=16777216
reads=0


def load(path,size=None,digest=None,json_value=True):
    global reads
    assert not path.is_symlink() and path.is_file()
    raw=path.read_bytes();reads+=len(raw);assert reads<=READ_LIMIT
    if size is not None:assert len(raw)==size
    if digest is not None:assert hashlib.sha256(raw).hexdigest()==digest
    return (json.loads(raw) if json_value else raw),{'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def main():
    failure,fr=load(BASE/'retained-journal/failure.json',100561,'c01dcb0c1a8c3737bce68c419e810c004230c3dd0923102065ea01ded54e7de7')
    export,er=load(BASE/'post-run-owner-export.local.json',3893676,'ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66')
    packet,qr=load(BASE/'packet.local.json',7339,'3b29761579efaabee4ef03c6c71ae5f476ced64980fa6d362c5eea55489457ec')
    protocol,pr=load(ROOT/'configs/e02_wrapper_crossmodel_v1_20261115.json',82688,'19fff8964e84c536d7b3969eeab18e1a14bff69744b7752c7fbe9b22d68cccc1')
    sources={};trees={}
    for name in ('wrapper_crossmodel_v1','wrapper_crossmodel_v1_owner','wrapper_crossmodel_v1_client'):
        raw,sr=load(ROOT/f'src/civiclab/e02/{name}.py',json_value=False);sources[name]=sr;trees[name]=ast.parse(raw)
    owner=export['wrapper_crossmodel'];receipts=owner['receipts'];rows=export['rows'];diag=failure['diagnostic']
    attempts=[]
    for receipt in receipts:
        row=rows[receipt];c=row['context'];order=int(c['unit_id'].rsplit('-',1)[1])
        attempts.append({'execution_order':order,'phase':c['phase'],'status':row['status'],'reserved_microusd':row['reserved'],'charged_microusd':row['charged'],'generation_id_present':row.get('generation_id') is not None})
    assert sorted(r['execution_order'] for r in attempts)==list(range(45))
    assert [w['execution_order'] for w in owner['witnesses']]==list(range(44))
    assert all(r['status']=='PHASE_COMMITTED' for r in attempts[:44])
    assert attempts[-1]['execution_order']==44 and attempts[-1]['status']=='UNCERTAIN' and attempts[-1]['charged_microusd']==attempts[-1]['reserved_microusd']==775 and not attempts[-1]['generation_id_present']
    assert owner['stopped'] is True and export['unfinished']==5 and owner['historical_unfinished']==4 and owner['pending'] is None
    assert (failure['model_POST_attempts'],failure['statistics_GET_attempts'],failure['catalog_GET_attempts'])==(45,44,10)
    assert diag['transport']['http_status']==402 and diag['reported_provider_cost_microusd'] is None and diag['reserved_microusd']==775
    assert len(export['history'])==1180 and len(rows)==194
    limits=packet['policy']['limits'];assert (limits['new_model_POSTs'],limits['new_statistics_GETs'],limits['catalog_GETs'])==(80,240,16)
    assert (limits['new_batch_microusd'],limits['cumulative_E02_microusd'],limits['shared_microusd'],limits['E01_microusd'])==(200000,1000000,5000000,0)
    ownerclass=next(n for n in trees['wrapper_crossmodel_v1_owner'].body if isinstance(n,ast.ClassDef) and n.name=='WrapperCrossmodelOwnerV1')
    methods={n.name:n for n in ownerclass.body if isinstance(n,ast.FunctionDef)}
    walk=next(n for n in trees['wrapper_crossmodel_v1'].body if isinstance(n,ast.FunctionDef) and n.name=='_walk')
    records=next(n for n in trees['wrapper_crossmodel_v1'].body if isinstance(n,ast.FunctionDef) and n.name=='_validate_records')
    def find_text(node,needle):
        return [{'line':n.lineno,'condition':ast.unparse(n.test)} for n in ast.walk(node) if isinstance(n,ast.If) and needle in ast.unparse(n.test)]
    clauses={'owner_reserve_returns_stopped':find_text(methods['reserve_next'],"study['stopped']"),'owner_grant_rejects_stopped_and_unfinished':find_text(methods['_apply'],"study['pending'] is not None or study['stopped']"),'owner_start_requires149predecessor':find_text(methods['_apply'],"state['consumed']['dispatches'] != 149"),'walk_failure_is_terminal':find_text(walk,'FAILED_UNCERTAIN'),'envelope_rejects_attempt_after_halt':find_text(records,"halt and status != 'NOT_ATTEMPTED'")}
    assert all(clauses.values())
    nextjob=protocol['jobs'][45];assert (nextjob['execution_order'],nextjob['model_key'],nextjob['phase'],nextjob['baseline_execution_order'])==(45,'B','post',13)
    assert any(w['execution_order']==13 and w['phase']=='pre' for w in owner['witnesses'])
    safe_diag={k:diag[k] for k in ('executor_stage','model_POST_attempts','statistics_GET_attempts','reservation_recorded','reserved_microusd','reported_provider_cost_microusd','conservative_charged_microusd','automatic_retry')}
    safe_diag['transport_http_status']=diag['transport']['http_status']
    fifth=sum(r['charged_microusd'] for r in attempts);assert fifth==3928
    canary_counts={'POSTs':45+1,'statistics_GET_max':44+3,'catalog_GET_max':10+2,'owner_lifetime_dispatches':194+1}
    future_barriers=[n for n in limits['catalog_refresh_before_slots'] if n>=45]
    count_conflict={'already_consumed':10,'new_fresh_both_route_catalogs':2,'remaining_original_barriers':future_barriers,'original_refresh_GETs_remaining':2*len(future_barriers),'whole_suffix_total_if_unchanged_schedule':10+2+2*len(future_barriers),'original_catalog_cap':16,'canary_only_total':12}
    assert count_conflict['whole_suffix_total_if_unchanged_schedule']==18>16
    maxcall=limits['per_call_microusd'];used=export['consumed'];bounds={'hypothetical_max_one_call_reservation':maxcall,'old_fifth_charged_including_hold':fifth,'hypothetical_fifth_after_reserve':fifth+maxcall,'old_global_exposure_including_holds':used['total'],'hypothetical_global_after_reserve':used['total']+maxcall,'hypothetical_E02_after_reserve':used['modules']['E02']+maxcall,'E01_paid_inference':used['modules']['E01'],'NOT_AN_ACTUAL_RESERVATION':True}
    safe={'kind':'CLOSED_402_AND_CONTINUATION_CONSTRAINTS_OFFLINE','decision':'BLOCKED_UNDER_UNCHANGED_STOPPED_OWNER_AND_ABSORBING_PROTOCOL','input_refs':[fr,er,qr,pr],'source_refs':sources,'private_provider_or_answer_text_copied':False,'safe_failed_phase_diagnostic':safe_diag,'specific_original402cause':'UNKNOWN_NO_RETAINED_ERROR_METADATA','counts':{'POST_attempts':45,'statistics_GETs':44,'catalog_GETs':10,'committed_responses':44,'owner_rows':194,'owner_history_events':1180},'frozen_dispositions':[{'execution_order':j['execution_order'],'phase':j['phase'],'model_key':j['model_key'],'baseline_execution_order':j['baseline_execution_order'],'disposition':('PHASE_COMMITTED' if j['execution_order']<44 else 'FAILED_UNCERTAIN' if j['execution_order']==44 else 'NOT_ATTEMPTED')} for j in protocol['jobs']],'slot44_hold':attempts[-1],'never_attempted_slot_range':[45,79],'next_canary_metadata':{k:nextjob[k] for k in ('execution_order','phase','model_key','baseline_execution_order','base_execution_order','visibility','pair_seed')},'baseline13_authenticated_committed':True,'owner_stop_state':{'stopped':True,'unfinished':5,'historical_unfinished':4,'pending_is_none':True,'refresh_stage':owner['refresh_stage']},'old_packet_lease':{k:packet['policy'][k] for k in ('valid_from_utc','valid_until_utc')},'original_limits':limits,'source_blocking_clauses':clauses,'hypothetical_one_canary_aggregate_counts':canary_counts,'catalog_schedule_conflict':count_conflict,'hypothetical_financial_bounds':bounds,'actual_new_reservations':0,'actual_owner_accesses_or_writes':0,'API_or_catalog_or_statistics_requests':0,'source_or_model_execution':False,'account_balance_or_management_authority_inferred':False,'application_bytes_read':reads,'resource_limits':{'CPU_seconds':60,'wall_seconds':90,'application_read_bytes':READ_LIMIT,'network_requests':0,'temp_data_writes':0},'evidence_note':'Loads only pinned closed snapshots and public source AST. Witness answers are held transiently for structure checking but never copied or printed; no production owner/client is instantiated/imported. Hypothetical arithmetic is not authority or a quote.'}
    with open(E/'closed-preflight.json','x') as stream:stream.write(json.dumps(safe,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'decision':safe['decision'],'input_bytes':reads,'counts':safe['counts'],'slot44_hold_microusd':775,'next_slot':45,'catalog_schedule_total_vs_cap':[18,16],'actual_API_calls':0,'actual_owner_actions':0},sort_keys=True))


if __name__=='__main__':main()
