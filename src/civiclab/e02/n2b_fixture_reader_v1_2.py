"""TEST_ONLY retained-state reader. No Control construction or actual reader."""
from . import n2b_admission_v1_2 as a
from .full_adult_types_v1_2 import strict_json
from .n2b_storage_v1_1_1 import directory
from .n2b_metrics_v1_1_1 import read_bytes,read_text
from .national_budget import Blocked


def read_state(realm):
 if type(realm) is not a.Realm or realm.kind!='TEST_ONLY' or realm.token is not a.TEST or realm.root not in a.TEST_ROOTS:raise Blocked('only registered authored realm; no actual reader')
 if read_text(realm.root/'TEST_ONLY_N2B')!=str(realm.root)+'\n':raise Blocked('authored root marker')
 path=realm.root/'data/processed/e02_n2b_private_v1/core';directory(path,realm.root,required=True)
 state=strict_json(read_bytes(path/'state.json'))
 if state.get('realm')!='TEST_ONLY' or state.get('schema')!='E02_N2B_PROSPECTIVE_CONTROL_V1_2':raise Blocked('authored state scope')
 return state
