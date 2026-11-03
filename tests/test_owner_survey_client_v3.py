"""Owner epoch/request integration with authored approvals and fake billing only."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from civiclab.common import atomic_json, canonical_hash
from civiclab.e02.experiment import assignments
from civiclab.model import ExecutionBlocked
from civiclab.owner_budget_v3 import OwnerBudgetFixtureV3, SCOPE
from civiclab.owner_survey_client_v3 import OwnerSurveyFixtureClientV3, create_live_owner_survey_client
from civiclab.reconciled_client_v2 import FixtureHTTP, fixture_terms
from civiclab.survey_envelope_v2 import compile_envelope, prepare_phase

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = json.loads((ROOT/'configs/e02_instrument.json').read_text())
STIMULI = json.loads((ROOT/'configs/e02_demo_stimuli.json').read_text())
T0 = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


def make_plan(terms):
    job = assignments([{'profile_id':'AUTHORED-OWNER-CLIENT', 'party':'D'}], STIMULI[:1], 20261103)[0]
    return compile_envelope(job, INSTRUMENT, terms, max_tokens=32)


def grant(owner, plan, total=100000, *, now=T0, **changes):
    snap = owner.snapshot()
    a = {'kind':SCOPE, 'approval_id':uuid.uuid4().hex, 'owner_id':snap['owner_id'],
         'previous_approval_hash':snap['approval_hash'], 'valid_from_utc':(now-timedelta(seconds=1)).isoformat(),
         'valid_until_utc':(now+timedelta(seconds=30)).isoformat(), 'total_microusd':total,
         'module_microusd':{'E01':total, 'E02':total}, 'allowed_plans':{canonical_hash(plan):{
             'module':'E02', 'terms_sha256':canonical_hash(plan['terms']), 'max_tokens':plan['max_tokens'],
             'max_input_token_bound':max(plan['pre_quote']['input_token_bound'], plan['post_bound']['input_token_bound'])}}}
    a.update(changes)
    return owner.grant_fixture(a)


def checkpoint(owner, result):
    c = result['context']; path = owner.directory/('phase-'+result['receipt']+'.local.json')
    atomic_json(path, {'schema_version':1, 'run_id':c['run_id'], 'unit_id':c['unit_id'],
                      'phase':c['phase'], 'receipt':result['receipt'],
                      'request_hash':c['envelope']['request_hash'], 'output':result['answer']})
    owner.commit_phase(result['receipt'], path)


class OwnerSurveyClientTests(unittest.TestCase):
    @contextmanager
    def case(self, *, terms=None, content=None, overrides=None, approved=True):
        with tempfile.TemporaryDirectory() as d:
            now = [T0]
            def clock():
                if isinstance(now[0], BaseException): raise now[0]
                return now[0]
            owner = OwnerBudgetFixtureV3.create_fixture(Path(d)/'owner', clock=clock)
            terms = terms or fixture_terms(); plan = make_plan(terms)
            epoch = grant(owner, plan) if approved else '0'*64
            transport = FixtureHTTP(terms, content=content, overrides=overrides)
            client = OwnerSurveyFixtureClientV3(owner, terms, transport)
            yield owner, plan, epoch, transport, client, now

    def call(self, case, *, phase='pre', before=None, **changes):
        owner, plan, epoch, transport, client, now = case
        args = {'expected_plan_hash':canonical_hash(plan), 'expected_approval_hash':epoch,
                'run_id':'authored-owner-client', 'phase':phase, 'before':before}
        args.update(changes)
        return client.complete(plan, **args)

    def unchanged(self, owner):
        return (owner.db_path.read_bytes(), owner.anchor.read_bytes(), owner.guard.read_bytes())

    def test_exact_payload_reservation_billing_and_external_checkpoint(self):
        with self.case() as c:
            owner, plan, epoch, http, client, now = c
            original = http.post; seen = []
            def post(payload):
                snap = owner.snapshot(); row = snap['charges'][0]
                self.assertEqual(row['status'], 'STARTED')
                self.assertEqual(row['charged'], plan['pre_quote']['reserved_microusd'])
                seen.append(deepcopy(payload)); return original(payload)
            with patch.object(http, 'post', side_effect=post): result = self.call(c)
            self.assertEqual([v[0] for v in http.calls], ['POST','GET_STATS'])
            context = result['context']; payload = seen[0]
            self.assertEqual(context['approval_hash'], epoch)
            self.assertEqual(context['plan_hash'], canonical_hash(plan))
            self.assertEqual(context['unit_id'], canonical_hash(plan['job']))
            self.assertEqual(context['sampling'], {'seed':plan['job']['pair_seed'], 'temperature':0, 'retries':0})
            self.assertEqual(context['payload_hash'], canonical_hash(payload))
            self.assertEqual(payload['messages'], prepare_phase(plan,'pre',expected_plan_hash=canonical_hash(plan))['messages'])
            self.assertEqual(payload['provider']['only'], [plan['terms']['requested_route']])
            self.assertFalse(payload['provider']['allow_fallbacks']); self.assertEqual(payload['plugins'],[])
            exact = sum(Decimal(plan['terms'][k]) for k in ('input_usd_per_token','output_usd_per_token','request_fee_usd'))
            self.assertEqual(result['charged_microusd'], int((exact*1000000).to_integral_value(rounding=ROUND_CEILING)))
            self.assertEqual(owner.snapshot()['charges'][0]['status'], 'SETTLED')
            calls = len(http.calls)
            with self.assertRaises(ExecutionBlocked): self.call(c, phase='post', before=result['answer']['parsed'])
            self.assertEqual(len(http.calls), calls)
            checkpoint(owner, result)
            self.assertEqual(owner.snapshot()['charges'][0]['status'], 'PHASE_COMMITTED')
            post_result = self.call(c, phase='post', before=result['answer']['parsed'])
            self.assertEqual(post_result['context']['approval_hash'], epoch)
            checkpoint(owner, post_result)
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'], 4)
            self.assertEqual(result['scope'], SCOPE)

    def test_no_approval_stale_expired_and_insufficient_caps_zero_post(self):
        with self.case(approved=False) as c:
            before = self.unchanged(c[0])
            with self.assertRaises(ExecutionBlocked): self.call(c)
            self.assertEqual(self.unchanged(c[0]), before); self.assertEqual(c[3].calls,[])
        for variant in ('stale','expired','total','module','plan'):
            with self.subTest(variant=variant), self.case() as c:
                owner, plan, epoch, http, client, now = c; changes={}
                if variant=='stale': changes['expected_approval_hash']='0'*64
                elif variant=='expired': now[0]=T0+timedelta(minutes=1)
                else:
                    kwargs={'total_microusd':1} if variant=='total' else {'module_microusd':{'E01':100000,'E02':0}} if variant=='module' else {'allowed_plans':{'a'*64:{'module':'E02','terms_sha256':canonical_hash(plan['terms']),'max_tokens':32,'max_input_token_bound':100000}}}
                    changes['expected_approval_hash']=grant(owner,plan,**kwargs)
                before = self.unchanged(owner)
                with self.assertRaises(ExecutionBlocked): self.call(c, **changes)
                self.assertEqual(self.unchanged(owner), before); self.assertEqual(http.calls,[])

    def test_changed_plan_source_seed_and_external_hash_zero_side_effects(self):
        edits = [lambda p:p['pre_quote'].__setitem__('reserved_microusd',1),
                 lambda p:p['source_pins'].__setitem__('model.py','0'*64),
                 lambda p:p['job'].__setitem__('pair_seed',True),
                 lambda p:p['job']['profile'].__setitem__('party','R')]
        for edit in edits:
            with self.case() as c:
                original_hash=canonical_hash(c[1]); edit(c[1]); before=self.unchanged(c[0])
                with self.assertRaises((ValueError, ExecutionBlocked)):
                    self.call(c, expected_plan_hash=original_hash)
                self.assertEqual(self.unchanged(c[0]),before); self.assertEqual(c[3].calls,[])
        with self.case() as c:
            p=deepcopy(c[1]);p['job']['pair_seed']=True
            replacement=compile_envelope(p['job'], INSTRUMENT, p['terms'], max_tokens=32)
            epoch=grant(c[0],replacement); before=self.unchanged(c[0])
            with self.assertRaises(ValueError):
                c[4].complete(replacement, expected_plan_hash=canonical_hash(replacement), expected_approval_hash=epoch, run_id='x', phase='pre')
            self.assertEqual(self.unchanged(c[0]),before);self.assertEqual(c[3].calls,[])

    def test_invalid_pre_answers_skip_without_events_or_fake_calls(self):
        invalids=[None,{},[],{'democratic_party':True,'republican_party':1},
                  {'democratic_party':float('nan'),'republican_party':1},
                  {'democratic_party':float('inf'),'republican_party':1},
                  {'democratic_party':101,'republican_party':1}]
        with self.case() as c:
            before=self.unchanged(c[0])
            for value in invalids:
                result=self.call(c,phase='post',before=value)
                self.assertEqual(result,{'status':'SKIPPED_INVALID_PRE','request':None,'messages':None,'quote':None})
            self.assertEqual(self.unchanged(c[0]),before);self.assertEqual(c[3].calls,[])

    def test_ledger_transport_type_and_terms_changes_refuse_before_dispatch(self):
        with self.case() as c:
            owner, plan, epoch, http, client, now=c; before=self.unchanged(owner)
            for ledger,transport in ((object(),http),(owner,object())):
                with self.assertRaises(ExecutionBlocked): OwnerSurveyFixtureClientV3(ledger,plan['terms'],transport)
            with patch('civiclab.owner_budget_v3.production_owner_directory',side_effect=AssertionError('resolver called')):
                with self.assertRaises(ExecutionBlocked):create_live_owner_survey_client()
            for target in (client.terms,http.terms):
                saved=deepcopy(target);target['request_fee_usd']='0.000001'
                with self.assertRaises(ExecutionBlocked):self.call(c)
                target.clear();target.update(saved)
            client.transport=object()
            with self.assertRaises(ExecutionBlocked):self.call(c)
            self.assertEqual(self.unchanged(owner),before);self.assertEqual(http.calls,[])

    def test_caller_alias_changes_at_reserve_do_not_change_admitted_payload(self):
        with self.case() as c:
            owner, plan, epoch, http, client, now=c
            before_answer={'democratic_party':60,'republican_party':40};original=owner.reserve
            frozen_plan=deepcopy(plan);seen=[];post=http.post
            def reserve(context):
                plan['job']['profile']['party']='R';before_answer['democratic_party']=99
                return original(context)
            def capture(payload):seen.append(deepcopy(payload));return post(payload)
            with patch.object(owner,'reserve',side_effect=reserve),patch.object(http,'post',side_effect=capture):
                result=self.call(c,phase='post',before=before_answer)
            expected=prepare_phase(frozen_plan,'post',expected_plan_hash=canonical_hash(frozen_plan),before={'democratic_party':60,'republican_party':40})
            self.assertEqual(seen[0]['messages'],expected['messages'])
            self.assertEqual(result['context']['plan_hash'],canonical_hash(frozen_plan))
            self.assertEqual(result['context']['envelope'],expected['quote'])

    def test_expiry_rollback_and_unavailable_clock_account_known_charge(self):
        for clock_value,expected_status in ((T0+timedelta(minutes=1),'OK'),(T0-timedelta(seconds=1),'CLOCK_ROLLBACK'),(RuntimeError('PRIVATE-CLOCK-ERROR'),'CLOCK_UNAVAILABLE')):
            with self.subTest(clock=expected_status), self.case() as c:
                owner,plan,epoch,http,client,now=c;post=http.post
                def late(payload):now[0]=clock_value;return post(payload)
                with patch.object(http,'post',side_effect=late):result=self.call(c)
                self.assertEqual(result['context']['approval_hash'],epoch)
                self.assertEqual(result['charged_microusd'],2)
                checkpoint(owner,result)
                snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['total'],2)
                import sqlite3
                with sqlite3.connect(owner.db_path) as db:
                    event=json.loads(db.execute('SELECT data FROM events ORDER BY sequence DESC LIMIT 1').fetchone()[0])['body']
                self.assertEqual(event['clock_status'],expected_status)
                if expected_status=='CLOCK_UNAVAILABLE':self.assertIsNone(event['recorded_at_utc'])
                calls=len(http.calls)
                with self.assertRaises(ExecutionBlocked):self.call(c,phase='post',before=result['answer']['parsed'])
                self.assertEqual(len(http.calls),calls)
                now[0]=T0+timedelta(minutes=2);new_epoch=grant(owner,plan,now=now[0]);before=self.unchanged(owner)
                with self.assertRaises(ExecutionBlocked):self.call(c,phase='post',before=result['answer']['parsed'])
                self.assertEqual(self.unchanged(owner),before)
                result2=self.call(c,phase='post',before=result['answer']['parsed'],expected_approval_hash=new_epoch)
                checkpoint(owner,result2)
                self.assertEqual(owner.snapshot()['consumed_microusd']['total'],4)

    def test_invalid_visible_answers_are_charged_quality_failures(self):
        for content in ('not JSON','[]','{"democratic_party":101,"republican_party":40}','{"democratic_party":NaN}'):
            with self.case(content=content) as c:
                result=self.call(c);self.assertEqual(result['charged_microusd'],2)
                checkpoint(c[0],result)
                self.assertEqual(c[0].snapshot()['charges'][0]['status'],'PHASE_COMMITTED')
                self.assertEqual([x[0] for x in c[3].calls],['POST','GET_STATS'])

    def test_bad_response_and_billing_retain_barrier_and_known_cost(self):
        variants=[{'response':{'id':'wrong'}},{'response':{'model':'wrong'}},
                  {'stats':{'provider_name':'wrong'}},{'stats':{'is_byok':True}},
                  {'stats':{'native_tokens_reasoning':1}},{'stats':{'native_tokens_completion':33}},
                  {'stats':{'total_cost':0.000003}},{'response':{'usage':{'cost':0.5}}}]
        for overrides in variants:
            with self.subTest(overrides=overrides), self.case(overrides=overrides) as c:
                with self.assertRaises(ExecutionBlocked):self.call(c)
                rows=c[0].snapshot()['charges'];self.assertEqual(len(rows),1)
                self.assertIn(rows[0]['status'],('UNCERTAIN','OVERRUN'))
                self.assertGreaterEqual(rows[0]['charged'],rows[0]['reserved'])
                if overrides.get('response',{}).get('usage'):self.assertGreaterEqual(rows[0]['charged'],500000)
                calls=len(c[3].calls)
                with self.assertRaises(ExecutionBlocked):self.call(c,run_id='another')
                self.assertEqual(len(c[3].calls),calls)
                self.assertEqual(sum(v[0]=='POST' for v in c[3].calls),1)
                with self.assertRaises(ExecutionBlocked):grant(c[0],c[1],total=1000000)

    def test_statistics_failure_and_cancellation_preserve_original_epoch(self):
        for error in (RuntimeError('PRIVATE-PROVIDER-BODY'),KeyboardInterrupt('PRIVATE-CANCEL')):
            with self.case() as c:
                with patch.object(c[3],'stats',side_effect=error):
                    with self.assertRaises(ExecutionBlocked if isinstance(error,Exception) else KeyboardInterrupt) as caught:self.call(c)
                if isinstance(error,Exception):self.assertNotIn('PRIVATE',str(caught.exception))
                row=c[0].snapshot()['charges'][0]
                self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['observed_cost'],2)
                self.assertEqual(row['context']['approval_hash'],c[2]);self.assertIsNotNone(row['generation_id'])
                self.assertEqual(sum(v[0]=='POST' for v in c[3].calls),1)

    def test_duplicate_generation_across_renewal_refuses_before_stats(self):
        with self.case() as c:
            first=self.call(c);checkpoint(c[0],first)
            epoch=grant(c[0],c[1]);c[3].overrides['response']={'id':first['billing']['id']}
            calls=len(c[3].calls)
            with self.assertRaises(ExecutionBlocked):self.call(c,phase='post',before=first['answer']['parsed'],expected_approval_hash=epoch)
            self.assertEqual([v[0] for v in c[3].calls[calls:]],['POST'])
            self.assertEqual(c[0].snapshot()['charges'][-1]['status'],'UNCERTAIN')

    def test_fractional_fee_rounding_lifetime_consumption_across_renewal(self):
        terms=fixture_terms();terms.update(input_usd_per_token='0.0000000001',output_usd_per_token='0',request_fee_usd='0.0000001')
        with self.case(terms=terms,approved=False) as c:
            epoch=grant(c[0],c[1],total=1)
            first=self.call(c,expected_approval_hash=epoch);checkpoint(c[0],first)
            self.assertEqual(first['charged_microusd'],1)
            calls=len(c[3].calls)
            with self.assertRaises(ExecutionBlocked):self.call(c,phase='post',before=first['answer']['parsed'],expected_approval_hash=epoch)
            self.assertEqual(len(c[3].calls),calls)
            epoch=grant(c[0],c[1],total=2)
            second=self.call(c,phase='post',before=first['answer']['parsed'],expected_approval_hash=epoch);checkpoint(c[0],second)
            self.assertEqual(c[0].snapshot()['consumed_microusd']['total'],2)
            self.assertEqual(second['charged_microusd'],1)

    def test_oversized_response_or_failed_post_never_refunds_or_retries(self):
        for mode in ('oversized','failed'):
            with self.case() as c:
                if mode=='oversized':c[3].content='X'*2_000_001
                else:
                    def fail(payload):c[3].calls.append(('POST','attempt'));raise RuntimeError('PRIVATE-BODY')
                with patch.object(c[3],'post',side_effect=fail) if mode=='failed' else context_noop():
                    with self.assertRaises(ExecutionBlocked):self.call(c)
                row=c[0].snapshot()['charges'][0]
                self.assertEqual(row['status'],'UNCERTAIN');self.assertGreaterEqual(row['charged'],row['reserved'])
                self.assertEqual([v[0] for v in c[3].calls],['POST'])


@contextmanager
def context_noop():yield
