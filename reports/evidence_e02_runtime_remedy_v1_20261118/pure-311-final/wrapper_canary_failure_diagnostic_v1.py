"""Closed secret-free error marker. No financial, request or retry authority."""
from ..common import canonical_bytes
from ..model import ExecutionBlocked
from ..production_compatibility_transport_v4_2 import _SafeTransportFailure

STAGES=frozenset(('ENTRY','JOURNAL','CATALOG_A','CATALOG_B','PROOFS','GRANT','REQUEST','POST','RESPONSE','STATISTICS_CLAIM','STATISTICS','INVOICE','CHECKPOINT','COMMIT','SUMMARY'))
FILENAME='failure-initial-v1.json'
MAXIMUM_BYTES=512


def failure_record(error,stage,provenance='MOCK'):
    if type(stage) is not str or stage not in STAGES:raise ValueError('closed diagnostic stage required')
    if type(provenance) is not str or provenance not in ('MOCK','EXPLORATORY_REAL_MODEL'):raise ValueError('closed diagnostic provenance required')
    # Never inspect args, repr, arbitrary attributes or exception descriptors.
    classes=((ExecutionBlocked,'EXECUTION_BLOCKED'),(ValueError,'VALUE_ERROR'),(TypeError,'TYPE_ERROR'),(TimeoutError,'TIMEOUT'),(OSError,'OS_ERROR'),(RuntimeError,'RUNTIME_ERROR'),(KeyboardInterrupt,'INTERRUPTED'),(SystemExit,'SYSTEM_EXIT'))
    kind=next((label for cls,label in classes if type(error) is cls),'OTHER');status=None
    if type(error) is _SafeTransportFailure:
        kind='SAFE_TRANSPORT_FAILURE'
        try:fields=object.__getattribute__(error,'_fields')
        except AttributeError:fields=None
        if type(fields) is not tuple or len(fields)!=4:
            kind='INVALID_TRANSPORT_DIAGNOSTIC'
        else:
            try:
                # Constructor revalidates exact primitive types/closed values.
                checked=_SafeTransportFailure(*fields)
                value=_SafeTransportFailure.diagnostic(checked)['http_status']
                if type(value) is int and 100<=value<=599:status=value
            except (ValueError,TypeError):kind='INVALID_TRANSPORT_DIAGNOSTIC'
    result={'kind':'WRAPPER_CANARY_INITIAL_FAILURE_V1','stage':stage,'error_kind':kind,'http_status':status,
            'response_provenance':provenance,'retry_allowed':False,
            'dispatch_generation_billing':'NOT_ATTESTED_BY_THIS_MARKER'}
    if len(canonical_bytes(result))>MAXIMUM_BYTES:raise ValueError('diagnostic bound exceeded')
    return result


def write_initial_failure(journal,error,stage,provenance='MOCK'):
    """Return only after existing journal file+directory fsync succeeds.

    Failure is surfaced to caller; it must preserve original exception and still
    attempt conservative cleanup. A partially written file is not a durability
    receipt. Fixed O_EXCL journal name forbids replacement/retry.
    """
    value=failure_record(error,stage,provenance)
    journal.write(FILENAME,value)
    return value
