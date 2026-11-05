"""Authored questionnaire content; no provider/billing observations."""
import json
import unittest

from civiclab.common import canonical_bytes
from civiclab.e02.exploratory_response_v1 import parse_survey_response


def response(text):
    return {'choices': [{'message': {'content': text}}]}


class SurveyResponseTests(unittest.TestCase):
    def test_preserves_valid_and_invalid_survey_json_without_repair(self):
        for answer in ({'democratic_party': 0, 'republican_party': 100},
                       {'democratic_party': None, 'republican_party': True},
                       {'other': 40}, None, [50, 50], 7, 'invalid survey shape'):
            with self.subTest(answer=answer):
                self.assertEqual(parse_survey_response(response(json.dumps(answer))),
                                 {'status': 'ANSWER', 'answer': answer, 'diagnostic': None})

    def test_duplicate_nonfinite_or_extra_text_is_explicit_parse_error(self):
        for text in ('{"x":1,"x":2}', 'NaN', 'Infinity', '1e400', '{} trailing',
                     '```json\n{}\n```', ''):
            result = parse_survey_response(response(text))
            self.assertEqual(result['status'], 'PARSE_ERROR')
            self.assertIsNone(result['answer'])

    def test_exact_visible_message_and_no_reasoning(self):
        for value in (None, {}, {'choices': []}, {'choices': [{}, {}]},
                      response(None), response(['not visible text'])):
            self.assertEqual(parse_survey_response(value)['status'], 'PARSE_ERROR')
        for field, value in [('reasoning', 'hidden'), ('reasoning_details', [{}])]:
            value_response = response('{}'); value_response['choices'][0]['message'][field] = value
            self.assertEqual(parse_survey_response(value_response)['diagnostic'], 'UNEXPECTED_REASONING')

    def test_content_utf8_number_key_string_and_depth_boundaries(self):
        cases = [('"'+'a'*257+'"'), json.dumps({'k'*65: 1}), '1'*33,
                 '['*10+'0'+']'*10, ' '*2049, '"'+'é'*1024+'"', '"\ud800"']
        for text in cases:
            self.assertEqual(parse_survey_response(response(text))['status'], 'PARSE_ERROR')
        for text in ('1'*32, json.dumps({'k'*64: 'a'*256}), '['*8+'0'+']'*8):
            self.assertEqual(parse_survey_response(response(text))['status'], 'ANSWER')

    def test_32_largest_retained_answers_fit_analysis_envelope(self):
        # Near the content-byte bound, with each string inside its bound.
        text = json.dumps(['a'*250]*8, separators=(',', ':'))
        self.assertLessEqual(len(text.encode()), 2048)
        parsed = parse_survey_response(response(text))
        self.assertEqual(parsed['status'], 'ANSWER')
        rows = [{'execution_order': i//2, 'phase': 'pre' if i%2 == 0 else 'post',
                 'status': 'ANSWER', 'answer': parsed['answer']} for i in range(32)]
        envelope = {'response_provenance': 'MOCK', 'protocol_sha256': 'a'*64,
                    'projection_sha256': 'b'*64, 'assignment_sha256': 'c'*64, 'records': rows}
        self.assertLess(len(canonical_bytes(envelope)), 131072)
        self.assertTrue(all(len(canonical_bytes(row)) <= 3072 for row in rows))

    def test_detached_answer_does_not_modify_raw_or_claim_financial_success(self):
        original = response('{"democratic_party":50,"republican_party":60}')
        saved = canonical_bytes(original)
        parsed = parse_survey_response(original)
        parsed['answer']['democratic_party'] = 1
        self.assertEqual(canonical_bytes(original), saved)
        self.assertEqual(set(parsed), {'status', 'answer', 'diagnostic'})


if __name__ == '__main__':
    unittest.main()
