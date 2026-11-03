import unittest
from copy import deepcopy
from civiclab.e02.experiment import treatment, assignments, evaluate, MockSurvey
from civiclab.e02.instrument import change


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
                    rows.append({'profile_id':p,'stimulus_id':s,'repeat':0,'arm':arm,
                                 'change':{'status':'VALID','primary':2 if arm=='C2' else 0}})
        result=evaluate(rows,1)
        self.assertEqual(result['estimate_thermometer_points'],2)
        self.assertEqual(result['interval_95_crossed_bootstrap'],[2,2])
        with self.assertRaises(ValueError):evaluate(rows[:-1])
        with self.assertRaises(ValueError):evaluate(rows+[rows[0]])
