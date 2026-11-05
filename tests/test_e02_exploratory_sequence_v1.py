"""End-to-end authored pilot sequencing, not observed model responses."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes
from civiclab.model import ExecutionBlocked
from civiclab.e02.exploratory_sequence_v1 import next_action, create_actual_runner
from test_additional_compatibility_owner_v1 import materials

RAW = (Path(__file__).resolve().parents[1]/'configs/e02_exploratory_live_pilot_v1_1.json').read_bytes()
CONFIG = json.loads(RAW)


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.terms = materials('AUTHORED_SEQUENCE_ONLY')[0]['terms']

    def next(self, rows):
        return next_action(RAW, self.terms, canonical_bytes(rows))

    def reply(self, state, answer, status='ANSWER'):
        request = state['request']
        return {'execution_order': request['execution_order'], 'phase': request['phase'],
                'payload_sha256': request['payload_sha256'], 'status': status, 'answer': answer}

    def finish(self, rows):
        while True:
            state = self.next(rows)
            if state['status'] != 'REQUEST_READY_NOT_ADMITTED':
                return state
            r = state['request']; job = CONFIG['assignments'][r['execution_order']]
            amount = 0 if r['phase'] == 'pre' else 1 if job['arm'] == 'C1' else 3
            sign = 1 if job['profile']['party'] == 'D' else -1
            rows.append(self.reply(state, {'democratic_party': 50+sign*amount,
                                           'republican_party': 50-sign*amount}))

    def test_32_phase_pipeline_has_hand_computed_four_point_contrast(self):
        rows = []; state = self.finish(rows)
        self.assertEqual(len(rows), 32)
        self.assertEqual(state['status'], 'COMPLETE')
        self.assertEqual(state['analysis']['complete_blocks'], 8)
        self.assertEqual(state['analysis']['estimate_thermometer_points'], 4)
        self.assertEqual(state['analysis']['interval_95_descriptive_crossed_bootstrap'], [4, 4])
        self.assertEqual(state['response_provenance'], 'MOCK')
        self.assertFalse(state['actual_authority'])
        self.assertEqual(state, self.next(deepcopy(rows)))

    def test_post_contains_only_own_baseline_and_rejects_other_units_hash(self):
        first = self.next([])
        baseline = {'democratic_party': 23, 'republican_party': 81}
        rows = [self.reply(first, baseline)]
        post = self.next(rows)
        self.assertEqual(post['request']['request']['pre_response'], baseline)
        self.assertEqual(post['request']['execution_order'], 0)
        baseline['democratic_party'] = 24
        self.assertEqual(post['request']['request']['pre_response']['democratic_party'], 23)
        # An earlier response cannot retain the previously bound post payload.
        submitted = self.reply(post, {'democratic_party': 50, 'republican_party': 50})
        with self.assertRaises(ExecutionBlocked):
            self.next(rows+[submitted])

    def test_invalid_and_unparseable_pre_skip_exactly_their_post(self):
        for status, answer in [('ANSWER', {}), ('ANSWER', {'democratic_party': None,
                                                      'republican_party': 50}),
                               ('PARSE_ERROR', None)]:
            rows = [self.reply(self.next([]), answer, status)]
            state = self.next(rows)
            self.assertEqual(state['request']['execution_order'], 1)
            self.assertEqual(state['request']['phase'], 'pre')
            self.assertEqual(state['derived_records'][1]['status'], 'SKIPPED_INVALID_PRE')
            terminal = self.finish(rows)
            self.assertEqual(len(rows), 31)
            self.assertEqual(terminal['analysis']['complete_blocks'], 7)
            self.assertEqual(terminal['analysis']['excluded_blocks'], 1)

    def test_uncertain_or_cancelled_phase_stops_all_later_requests(self):
        for status in ('FAILED_UNCERTAIN', 'CANCELLED'):
            for phase in ('pre', 'post'):
                rows = []
                if phase == 'post':
                    rows.append(self.reply(self.next(rows), {'democratic_party': 50, 'republican_party': 50}))
                rows.append(self.reply(self.next(rows), None, status))
                terminal = self.next(rows)
                self.assertEqual(terminal['status'], 'STOPPED')
                self.assertEqual(terminal['consumed_responses'], len(rows))
                self.assertEqual(terminal['analysis']['status'], 'NOT_ESTIMABLE')
                self.assertEqual(len(terminal['response_envelope']['records']), 32)
                with self.assertRaises(ExecutionBlocked):
                    self.next(rows+[deepcopy(rows[-1])])

    def test_invalid_post_excludes_block_but_does_not_stop_study(self):
        rows = [self.reply(self.next([]), {'democratic_party': 50, 'republican_party': 50})]
        rows.append(self.reply(self.next(rows), None, 'PARSE_ERROR'))
        terminal = self.finish(rows)
        self.assertEqual(terminal['status'], 'COMPLETE')
        self.assertEqual(terminal['analysis']['complete_blocks'], 7)

    def test_closed_ordered_response_contract(self):
        row = self.reply(self.next([]), {'democratic_party': 50, 'republican_party': 50})
        mutations = [('execution_order', True), ('execution_order', 1), ('phase', 'post'),
                     ('payload_sha256', '0'*64), ('status', 'NOT_ATTEMPTED'),
                     ('extra', None)]
        for key, value in mutations:
            with self.subTest(key=key):
                altered = deepcopy(row); altered[key] = value
                with self.assertRaises(ExecutionBlocked):
                    self.next([altered])
        with self.assertRaises(ExecutionBlocked):
            self.next([row]*33)
        with self.assertRaises(ValueError):
            next_action(RAW, self.terms, b'[{"phase":"pre","phase":"post"}]')

    def test_no_credential_owner_or_network_access_and_actual_factory_denies(self):
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('os.environ', {}), \
             patch('civiclab.production_owner_v4.pwd.getpwuid', side_effect=AssertionError('owner')):
            self.assertEqual(self.next([])['status'], 'REQUEST_READY_NOT_ADMITTED')
            with self.assertRaises(ExecutionBlocked):
                create_actual_runner()


if __name__ == '__main__':
    unittest.main()
