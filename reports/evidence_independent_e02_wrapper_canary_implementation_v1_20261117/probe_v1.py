"""Independent finite MOCK/copy extensions. No actual API or live owner."""
import sys, importlib.util, hashlib, json, unittest
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT/'src'))
TEST = ROOT/'tests/test_wrapper_crossmodel_canary_v1.py'
assert hashlib.sha256(TEST.read_bytes()).hexdigest() == 'a07b111a9418078969fa267f4772d9a2ea95bbd72b2617ef02199aafe6ab1a24'
spec = importlib.util.spec_from_file_location('independent_frozen_canary_helpers', TEST)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import sqlite3

PINS = {
 h.BASE/'post-run-owner-export.local.json': (3893676, 'ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66'),
 h.BASE/'packet.local.json': (7339, '3b29761579efaabee4ef03c6c71ae5f476ced64980fa6d362c5eea55489457ec'),
 h.HISTORICAL_PRICES/'catalog-A.json': (2359, '59c4fcc5ec213b8aae3019949267bd0f27f6bdfc95bee436c06a85ffc8ef9ee9'),
 h.HISTORICAL_PRICES/'catalog-B.json': (3569, '59c512102ac025f51b2e8a0b038170b5f29901a4a68421dec926d074f9a02237'),
 h.HISTORICAL_PRICES/'receipt-A.json': (209, '369dc1b7598e4d506c2cfe828c224b6b888ef60ccf59c1bd5874d4c234890055'),
 h.HISTORICAL_PRICES/'receipt-B.json': (222, 'd27922de49f095deb34c2f72032339cd1e603c18adae2b12158c4bdde975fdc9'),
}
class IndependentCases(unittest.TestCase):
    setUp = h.CopiedHistoryCases.setUp
    tearDown = h.CopiedHistoryCases.tearDown
    bind = h.CopiedHistoryCases.bind
    execute = h.CopiedHistoryCases.execute
    preserved = h.CopiedHistoryCases.preserved
    ready = h.CopiedHistoryCases.ready
    @classmethod
    def setUpClass(cls):
        # Tighten author's broader closed-directory allowlist to six exact pins.
        def exact_closed_scope(event, args):
            if event == 'open' and not isinstance(args[0], int):
                p = Path(args[0]).absolute()
                if (p.is_relative_to(h.BASE) or p.is_relative_to(h.HISTORICAL_PRICES)) and p not in PINS:
                    raise AssertionError('UNPINNED_CLOSED_INPUT')
        sys.addaudithook(exact_closed_scope)
        raw = {}
        for p, (size, digest) in PINS.items():
            b = p.read_bytes()
            if len(b) != size or hashlib.sha256(b).hexdigest() != digest:
                raise AssertionError('CLOSED_INPUT_PIN')
            raw[p] = b
        cls.export = json.loads(raw[h.BASE/'post-run-owner-export.local.json'])
        cls.old_packet = json.loads(raw[h.BASE/'packet.local.json'])
        cls.historical_raw = {r: raw[h.HISTORICAL_PRICES/f'catalog-{r}.json'] for r in ('A','B')}
        cls.historical_receipts = {r: json.loads(raw[h.HISTORICAL_PRICES/f'receipt-{r}.json']) for r in ('A','B')}
        # Freshness is an authored clock assertion, never historical relabeling.
        cls.records = {r: {'body_utf8': cls.historical_raw[r].decode(), 'metadata': cls.historical_receipts[r]} for r in ('A','B')}
    def stop_case(self, mode):
        with self.assertRaises(BaseException):
            self.execute(mode)
        state = self.preserved()
        row = state['rows'][state[h.m.STATE]['receipt']]
        self.assertTrue(row['charged'] >= row['reserved'])
        self.assertTrue(row['status'] != 'PHASE_COMMITTED')
        self.assertEqual(self.transport.posts, 1)
        with self.assertRaises(h.ExecutionBlocked): self.owner.grant()
        with self.assertRaises(h.ExecutionBlocked): self.owner.open_canary(self.q, h.canonical_hash(self.q))
    def test_01_statistics_429_stops_once(self):
        self.stop_case('429')
        self.assertEqual(self.transport.gets, 1)
    def test_02_post_timeout_stops_once(self):
        self.stop_case('UNKNOWN')
        self.assertEqual(self.transport.gets, 0)
    def test_03_model_mismatch_stops_once(self):
        self.stop_case('MODEL')
        self.assertEqual(self.transport.gets, 0)
    def test_04_malformed_response_stops_once(self):
        original = h.Transport.post_bytes
        def malformed(t, raw):
            original(t, raw)
            return []
        with patch.object(h.Transport, 'post_bytes', malformed): self.stop_case('OK')
        self.assertEqual(self.transport.gets, 0)
    def test_05_delayed_404_then_success(self):
        result = self.execute('DELAY')
        self.assertEqual(result['status'], 'COMMITTED_ONE_SLOT')
        self.assertEqual((self.transport.posts, self.transport.gets), (1, 2))
        self.preserved()
    def test_06_generation_collision_retains_hold(self):
        generation = next(r['generation_id'] for r in self.export['rows'].values() if r['generation_id'])
        original = h.Transport.post_bytes
        def collision(t, raw):
            response = original(t, raw)
            response['id'] = generation
            return response
        with patch.object(h.Transport, 'post_bytes', collision): self.stop_case('OK')
        self.assertEqual(self.transport.gets, 0)
    def test_07_future_catalog_stops_before_reservation(self):
        original = self.catalog
        def future(model):
            raw, metadata = original(model)
            metadata['observed_at_utc'] = (self.now()+timedelta(seconds=1)).isoformat()
            return raw, metadata
        self.catalog = future
        with self.assertRaises(h.ExecutionBlocked): self.execute()
        state = self.preserved()
        self.assertEqual(len(state['rows']), 194)
        self.assertEqual(self.transport.posts, 0)
    def test_08_price_drift_stops_before_reservation(self):
        original = self.catalog
        def drift(model):
            raw, metadata = original(model)
            if model == self.q['price_release']['B']['terms']['model']:
                value = json.loads(raw)
                for endpoint in value['data']['endpoints']:
                    if endpoint.get('tag','').startswith('nebius/fp8'):
                        endpoint['pricing']['prompt'] = str(Decimal(endpoint['pricing']['prompt'])*2)
                raw = h.canonical_bytes(value)
                metadata['body_sha256'] = hashlib.sha256(raw).hexdigest()
            return raw, metadata
        self.catalog = drift
        with self.assertRaises(h.ExecutionBlocked): self.execute()
        state = self.preserved()
        self.assertEqual(len(state['rows']), 194)
        self.assertEqual(self.transport.posts, 0)
    def test_09_materialized_SQL_tamper_refused(self):
        with sqlite3.connect(self.owner.db_path) as db:
            key, data = db.execute('SELECT id,data FROM charges LIMIT 1').fetchone()
            row = json.loads(data)
            row['charged'] += 1
            db.execute('UPDATE charges SET data=? WHERE id=?', (json.dumps(row), key))
        with self.owner._lock(), self.owner._connect() as db:
            with self.assertRaises(h.ExecutionBlocked): self.owner._verify(db)

class CapabilityCases(unittest.TestCase):
    def test_10_capability_spent_even_when_transport_times_out(self):
        class Phase:
            def gate(self): pass
        class Journal:
            def __init__(self): self.writes = 0
            def write(self, *args): self.writes += 1
        class Transport:
            def __init__(self): self.calls = 0
            def post_bytes(self, raw): self.calls += 1; raise TimeoutError('MOCK')
        journal = Journal(); transport = Transport()
        ack = {'receipt':'a'*32,'head':{},'context':{},'request':{'payload_sha256':'b'*64,'payload':{'MOCK':True}}}
        cap = h.frozen._Capability(h.frozen._SEAL, journal, Phase(), transport, ack)
        with self.assertRaises(TimeoutError): cap.post()
        with self.assertRaises(h.ExecutionBlocked): cap.post()
        self.assertEqual((transport.calls, journal.writes), (1,1))

if __name__ == '__main__':
    # The reviewed author limiter supplies charged SQL reads, conservative
    # SQLite writes, descriptor guard, network/key/live-store denial and cleanup.
    sys.argv = [str(TEST), 'IndependentCases', 'CapabilityCases']
    raise SystemExit(h.bounded_main())
