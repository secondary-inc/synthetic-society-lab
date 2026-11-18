from pathlib import Path
import sys
root=Path.cwd();source=root/'tests/test_ci_collection_isolation_v1.py';extra=root/'reports/evidence_independent_ci_allocation_v2_20261118/additional_controls.py';raw=source.read_text();needle="if __name__=='__main__':raise SystemExit(bounded_main())";assert raw.count(needle)==1
raw=raw.replace(needle,extra.read_text()+'\n'+needle)
namespace={'__name__':'__main__','__file__':str(source),'__builtins__':__builtins__};exec(compile(raw,str(source),'exec'),namespace)
