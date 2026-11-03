import unittest
from copy import deepcopy
from civiclab.e02.experiment import treatment, assignments, evaluate, MockSurvey
from civiclab.e02.instrument import change
from civiclab.common import canonical_hash


STIM={'id':'DEMO','text':'Fictional source text.','source_label':'same source','qa':{'question':'q','answer':'a'}}


class ExperimentTests(unittest.TestCase):
    def test_content_attribution_and_qa_matched(self):
        arms={a:treatment(STIM,a) for a in ('C0','C1','C2','C3','C4')}
        self.assertEqual({arms[a]['body_sha256'] for a in ('C1','C2','C3','C4')},{arms['C1']['body_sha256']})
        self.assertEqual(arms['C1']['source_label'],arms['C2']['source_label'])
        self.assertEqual(arms['C3']['qa'],arms['C4']['qa'])
        self.assertEqual(arms['C0']['body'],'')
        self.assertEqual(STIM['text'],'Fictional source text.')

    def test_crossed_randomization_and_reset_context(self):
        profiles=[{'profile_id':f'p{i}','party':'D'} for i in range(4)]
        a=assignments(profiles,[STIM],12);b=assignments(profiles,[STIM],12)
        self.assertEqual(a,b)
        self.assertNotEqual(a,assignments(profiles,[STIM],13))
        self.assertEqual(len(a),20)
        self.assertEqual(len({(j['profile']['profile_id'],j['arm']) for j in a}),20)
        for profile in profiles:
            self.assertEqual(len({j['pair_seed'] for j in a if j['profile']['profile_id']==profile['profile_id']}),1)
        provider=MockSurvey()
        request={'seed':1,'profile':{'party':'D'},'phase':'pre','exposure':None}
        original=deepcopy(request);first=provider.respond(request)
        provider.respond({**request,'phase':'post','exposure':treatment(STIM,'C2')})
        self.assertEqual(provider.respond(request),first)
        self.assertEqual(request,original)

    def test_known_effect_recovery_and_incomplete_assignment_rejected(self):
        rows=[]
        for p in ('a','b','c'):
            for s in ('x','y'):
                for arm in ('C0','C1','C2','C3','C4'):
                    pre={'democratic_party':60,'republican_party':40}
                    post={'democratic_party':61 if arm=='C2' else 60,'republican_party':39 if arm=='C2' else 40}
                    rows.append({'profile_id':p,'stimulus_id':s,'repeat':0,'arm':arm,
                                 'pre':pre,'post':post,'scoring_party':'D','change':change(pre,post,'D')})
        result=evaluate(rows,1)
        self.assertEqual(result['estimate_thermometer_points'],2)
        self.assertEqual(result['interval_95_crossed_bootstrap'],[2,2])
        with self.assertRaises(ValueError):evaluate(rows[:-1])
        with self.assertRaises(ValueError):evaluate(rows+[rows[0]])

    def test_cached_scores_cannot_replace_raw_outcomes(self):
        rows=[]
        for arm in ('C0','C1','C2','C3','C4'):
            pre={'democratic_party':60,'republican_party':40}
            post={'democratic_party':60,'republican_party':40}
            rows.append({'profile_id':'p','stimulus_id':'s','repeat':0,'arm':arm,
                         'pre':pre,'post':post,'scoring_party':'D','change':change(pre,post,'D')})
        rows[2]['change']['primary']=80
        with self.assertRaisesRegex(ValueError,'cached derived score'):
            evaluate(rows)
        for row in rows:row.pop('pre')
        with self.assertRaisesRegex(ValueError,'raw before-and-after'):
            evaluate(rows)

    def test_frozen_requests_reject_rehashed_survey_phase_and_context_drift(self):
        survey={'instrument_id':'frozen','items':['democratic_party','republican_party']}
        jobs=assignments([{'profile_id':'p','party':'D'}],[STIM],12)
        rows=[]
        provider=MockSurvey()
        for job in jobs:
            pre_request={'phase':'pre','seed':job['pair_seed'],'profile':deepcopy(job['profile']),
                         'survey':deepcopy(survey),'item_order':deepcopy(job['item_order']),'exposure':None}
            pre=provider.respond(pre_request)
            post_request={**deepcopy(pre_request),'phase':'post','pre_response':deepcopy(pre),
                          'exposure':deepcopy(job['exposure'])}
            post=provider.respond(post_request)
            rows.append({'profile_id':'p','stimulus_id':STIM['id'],'repeat':0,'arm':job['arm'],
                         'pre':pre,'post':post,'scoring_party':'D',
                         'pre_request':pre_request,'post_request':post_request,
                         'request_hashes':[canonical_hash(pre_request),canonical_hash(post_request)]})
        self.assertEqual(evaluate(rows,expected_assignments=jobs,expected_instrument=survey)
                         ['frozen_assignment_validation'],'PASS')
        with self.assertRaisesRegex(ValueError,'frozen instrument required'):
            evaluate(rows,expected_assignments=jobs)
        for phase in ('pre','post'):
            for field,value in (('survey',{'instrument_id':'NONFROZEN_INSTRUMENT'}),
                                ('phase','post' if phase=='pre' else 'pre'),
                                ('unapproved_context','unassigned information')):
                altered=deepcopy(rows)
                altered[0][phase+'_request'][field]=value
                # A self-consistent hash cannot authorize a changed experimental request.
                altered[0]['request_hashes']=[canonical_hash(altered[0]['pre_request']),
                                               canonical_hash(altered[0]['post_request'])]
                with self.subTest(phase=phase,field=field):
                    with self.assertRaisesRegex(ValueError,'instrument or phase'):
                        evaluate(altered,expected_assignments=jobs,expected_instrument=survey)
