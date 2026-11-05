"""Bounded questionnaire-quality parsing, independent of billing/admission.

The client must first harvest monetary observations and verify response privacy,
identity and transport bounds. This parser grants no commit or dispatch right.
Raw provider evidence is retained separately; this function never truncates it.
"""
import json
import math

from ..common import canonical_bytes


def parse_survey_response(response):
    """Return exact bounded parsed JSON or an explicit quality failure.

    ANSWER means syntactically acceptable, not a valid survey score or a
    financially authenticated response. The original scoring/exclusions decide
    validity. All failures carry fixed enums and no copied exception text.
    """
    def failure(reason):
        return {'status': 'PARSE_ERROR', 'answer': None, 'diagnostic': reason}

    choices = response.get('choices') if type(response) is dict else None
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        return failure('CHOICE_SHAPE')
    message = choices[0].get('message')
    if type(message) is not dict:
        return failure('MESSAGE_SHAPE')
    if (message.get('reasoning') not in (None, '')
            or message.get('reasoning_details') not in (None, [])):
        return failure('UNEXPECTED_REASONING')
    text = message.get('content')
    if type(text) is not str:
        return failure('CONTENT_SHAPE')
    try:
        if len(text.encode('utf-8')) > 2048:
            return failure('CONTENT_BOUND')
    except UnicodeError:
        return failure('CONTENT_ENCODING')

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate')
            out[key] = value
        return out

    def reject(_):
        raise ValueError('nonfinite')

    def bound(value, depth=0):
        if depth > 8:
            raise ValueError('depth')
        if type(value) in (int, float):
            if (type(value) is float and not math.isfinite(value)) or len(canonical_bytes(value)) > 32:
                raise ValueError('number')
        elif type(value) is str:
            if len(value) > 256:
                raise ValueError('string')
        elif type(value) is list:
            for child in value:
                bound(child, depth+1)
        elif type(value) is dict:
            for key, child in value.items():
                if len(key) > 64:
                    raise ValueError('key')
                bound(child, depth+1)

    try:
        answer = json.loads(text, object_pairs_hook=pairs, parse_constant=reject)
        bound(answer)
        canonical_bytes(answer)
    except (ValueError, TypeError, RecursionError, OverflowError, UnicodeError):
        return failure('JSON_OR_REPRESENTATION_BOUND')
    return {'status': 'ANSWER', 'answer': answer, 'diagnostic': None}
