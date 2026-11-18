from pathlib import Path
root=Path.cwd();source=root/'tests/test_ci_collection_isolation_v1.py';extra=root/'reports/evidence_independent_ci_allocation_v2_20261118/additional_controls.py';raw=source.read_text();needle="if __name__=='__main__':raise SystemExit(bounded_main())";assert raw.count(needle)==1
raw=raw.replace(needle,extra.read_text()+'\n'+needle)
check='program=unittest.main(verbosity=2,exit=False)';assert raw.count(check)==1
raw=raw.replace(check,check+'\n        assert program.result.testsRun==66, "INDEPENDENT_EXACT_66_CASES_REQUIRED"')
__file__=str(source)
exec(compile(raw,str(source),'exec'),globals())
