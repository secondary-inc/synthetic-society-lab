"""Authored executable specification only; not a replacement runtime wrapper."""
import copy
import math
import unittest

from civiclab.e01 import ballots_v1_9 as old
from tests.test_e01_typed_readiness_v1_9 import base_fixture

# Static accepted Nebraska helper shape; no actual helper execution or sources.
BOUNDS = {'district': (151, 200), 'term': (200, 225), 'vote': (225, 253),
          'party': (253, 317), 'name': (317, 430), 'city': (430, 484), 'incumbency': (484, 540)}


def normalized(value, path=(), native=False):
    kind = type(value)
    if kind is tuple:
        old.require(native and len(path) == 3 and path[:2] == ('NE', 'physical_column_bounds'))
        old.require(path[2] in BOUNDS and len(value) == 2 and all(type(x) is int for x in value))
        old.require(value == BOUNDS[path[2]])
        return list(value)
    if kind is dict:
        old.require(all(type(k) is str for k in value))
        return {k: normalized(v, (*path, k), native) for k, v in value.items()}
    if kind is list:
        return [normalized(v, (*path, i), native) for i, v in enumerate(value)]
    if kind is float:
        old.require(math.isfinite(value))
    else:
        old.require(kind in (str, int, bool, type(None)))
    return value


def proposed_identity(rosters, public, references, bound_hashes):
    # This is a fixture-only narrow specification. Actual v1.9 code is unchanged.
    native = normalized(rosters, native=True)
    saved = normalized(references['legacy_rosters'])
    old.require(old.canonical_hash(native) == old.canonical_hash(saved))
    old.require(old.canonical_hash(normalized(public)) == old.canonical_hash(normalized(references['legacy_public'])))
    old.require(old.idaho.digest(old.encoded(rosters)) == bound_hashes['legacy_rosters'])
    old.require(old.idaho.digest(old.encoded(public)) == bound_hashes['legacy_public'])


def payloads():
    b = base_fixture()
    rosters = b.pop('local_only_rosters')
    rosters['NE']['physical_column_bounds'] = copy.deepcopy(BOUNDS)
    refs = {'legacy_rosters': old.idaho.strict_json(old.encoded(rosters)),
            'legacy_public': old.idaho.strict_json(old.encoded(b))}
    hashes = {k: old.idaho.digest(old.encoded(v)) for k, v in refs.items()}
    return rosters, b, refs, hashes


class NarrowIdentityProposalTests(unittest.TestCase):
    def test_only_known_NE_native_tuple_values_normalize_without_changing_bytes(self):
        rosters, public, refs, hashes = payloads()
        self.assertNotEqual(rosters, refs['legacy_rosters'])
        self.assertEqual(old.encoded(rosters), old.encoded(refs['legacy_rosters']))
        proposed_identity(rosters, public, refs, hashes)
        proposed_identity(refs['legacy_rosters'], public, refs, hashes)
        self.assertEqual(BOUNDS, old.legacy.ne.BOUNDS)

    def test_unrelated_tuple_wrong_bound_boolean_or_float_not_accepted_as_NE_exception(self):
        changes = [lambda r: r['AK'].update(candidates=tuple(r['AK']['candidates'])),
                   lambda r: r['NE']['physical_column_bounds'].update(district=(150, 200)),
                   lambda r: r['NE']['physical_column_bounds'].update(district=(True, 200)),
                   lambda r: r['NE']['physical_column_bounds'].update(district=(151.0, 200)),
                   lambda r: r['NE']['physical_column_bounds'].update(district=(151, 200, 201)),
                   lambda r: r['NE'].update(unrelated_tuple=('DEMO',))]
        for change in changes:
            r, p, refs, hashes = payloads(); change(r)
            with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)

    def test_all_twelve_object_field_member_and_UNKNOWN_changes_still_fail(self):
        for state in old.STATES:
            for change in [lambda x: x.update(extra='DEMO'), lambda x: x.pop('source_hashes'),
                           lambda x: x['observations'].update(final_ballot_accepted=True),
                           lambda x: x['candidates'][0].update(official_name='DEMO ALTERED')]:
                r, p, refs, hashes = payloads(); change(r[state])
                with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)
        r, p, refs, hashes = payloads(); r['ID'] = {}
        with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)

    def test_number_boolean_null_and_nested_source_identity_remain_distinct(self):
        for replacement in [False, 0, 0.0, None, 'UNKNOWN']:
            r, p, refs, hashes = payloads()
            r['AK']['source_hashes'][0] = replacement
            with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)
        for key, replacement in [('official_rosters_extracted', 12.0), ('source_adoption', 0),
                                 ('final_ballots_accepted', False), ('cost_usd', 0.0)]:
            r, p, refs, hashes = payloads(); p[key] = replacement
            with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)

    def test_coedited_references_do_not_replace_frozen_whole_payload_hash_authority(self):
        r, p, refs, hashes = payloads()
        r['AK']['candidates'][0]['official_name'] = 'DEMO COEDIT'
        refs['legacy_rosters']['AK']['candidates'][0]['official_name'] = 'DEMO COEDIT'
        with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)
        r, p, refs, hashes = payloads()
        p['source_adoption'] = refs['legacy_public']['source_adoption'] = True
        with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)

    def test_reference_custom_container_or_tuple_is_not_a_JSON_reference(self):
        r, p, refs, hashes = payloads()
        refs['legacy_rosters']['NE']['physical_column_bounds']['district'] = (151, 200)
        with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)
        class Custom(dict): pass
        r, p, refs, hashes = payloads(); r['NE'] = Custom(r['NE'])
        with self.assertRaises(ValueError): proposed_identity(r, p, refs, hashes)


if __name__ == '__main__':
    unittest.main()
