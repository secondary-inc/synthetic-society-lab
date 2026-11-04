"""Bounded read-only snapshot fixtures. No actual control or secret access."""
import sqlite3
import unittest
from unittest.mock import patch

from civiclab.common import canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.additional_compatibility_preflight_v1 import collect_actual,_collect_authored_snapshot
from test_additional_compatibility_owner_v1 import case,append


class ReadonlyPreflightTests(unittest.TestCase):
    def test_actual_entry_denies_before_os_or_arguments(self):
        class Bomb:
            def __getattribute__(self,key):raise AssertionError('argument access')
        with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('OS access')):
            with self.assertRaises(ExecutionBlocked):collect_actual(Bomb())

    def test_snapshot_proves_retained_unknown_and_leaves_all_control_bytes_unchanged(self):
        with case() as (owner,original,b,x,release,clock,old):
            before=owner.snapshot();snap=_collect_authored_snapshot()
            self.assertEqual(snap['predecessor_row'],old)
            self.assertEqual(snap['predecessor_row_hash'],canonical_hash(old))
            self.assertEqual(snap['history_hash'],b['policy']['prior_history_hash'])
            self.assertEqual(snap['head'],b['policy']['prior_head'])
            self.assertEqual(snap['unfinished'],1);self.assertFalse(snap['owner_writes'])
            self.assertEqual(owner.snapshot(),before)

    def test_every_sql_connection_is_readonly_and_query_only_enforced(self):
        with case():
            native=sqlite3.connect;opened=[]
            def connect(database_uri,**kw):
                self.assertTrue(database_uri.endswith('?mode=ro'));self.assertTrue(kw['uri'])
                db=native(database_uri,**kw)
                with self.assertRaises(sqlite3.OperationalError):db.execute('CREATE TABLE unintended (x)')
                opened.append(db);return db
            with patch('civiclab.additional_compatibility_preflight_v1.sqlite3.connect',side_effect=connect):
                _collect_authored_snapshot()
            self.assertEqual(len(opened),1)
            with self.assertRaises(sqlite3.ProgrammingError):opened[0].execute('SELECT 1')
            opened[0].close()

    def test_changed_or_missing_original_control_is_not_recreated(self):
        with case() as (owner,*_):
            raw=owner.anchor.read_bytes();owner.anchor.unlink()
            with self.assertRaises((ExecutionBlocked,FileNotFoundError)):_collect_authored_snapshot()
            self.assertFalse(owner.anchor.exists());self.assertTrue(raw)

    def test_successor_history_and_new_uncertainty_are_not_adopted_as_original(self):
        with case() as (owner,original,b,x,release,clock,old):
            append(owner,b,x,release)
            with self.assertRaises(ExecutionBlocked):_collect_authored_snapshot()


if __name__=='__main__':unittest.main()
