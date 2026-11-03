"""Versioned owned-root accounting remedy. Native caps/transition semantics unchanged."""
import shutil
from .f_wy_bootstrap_control_v1 import Control as OriginalControl, stamp, elapsed, ORDER
from .f_wy_bootstrap_v1 import require_bundle
from .national_budget import Blocked


class Control(OriginalControl):
    def __init__(self, bundle, *, create=False):
        b = require_bundle(bundle)
        marker = b.root / 'BOOTSTRAP_V1_1'
        if marker.is_symlink() or not marker.is_file() or marker.read_text() != 'MOCK_PATH_STORAGE_REMEDY_V1_1\n':
            raise Blocked('new v1.1 fixture lineage required; frozen v1 not adopted')
        super().__init__(b, create=create)

    def storage(self, *, category='core', extra=0, initial=False):
        require_bundle(self.b)
        if self.root != self.b.root / 'control' or self.c != self.b.source.config:
            raise Blocked('storage context differs from minted authored bundle')
        if type(extra) is not int or extra < 0:
            raise Blocked('invalid storage projection')
        q = self.c['storage']
        if category not in q['caps']:
            raise Blocked('unknown storage category')
        usage = {}
        # Scan the ENTIRE owned root once. This includes BUNDLE.local.json,
        # lineage metadata and unexpected root files, with no extra quota pool.
        for p in self.b.root.rglob('*'):
            if p.is_symlink():
                raise Blocked('private workspace symlink')
            if not p.is_file():
                continue
            parts = p.relative_to(self.b.root).parts
            local = parts[1:] if parts[0] in ('source', 'runtime', 'control') else ()
            if local[:1] == ('inputs',): k = 'raw'
            elif local[:1] == ('scratch',): k = 'scratch'
            elif parts[0] == 'runtime' and local[:1] in (('PRIMARY',), ('REPLAY',)): k = local[0]+':base'
            else: k = 'core'
            usage[k] = usage.get(k, 0) + p.stat().st_size
        # Check every owned filesystem root, without assuming pooled free bytes.
        for root in (self.b.root, self.b.root/'source', self.root, self.b.root/'runtime'):
            if root.is_symlink(): raise Blocked('storage root symlink')
            if root.exists() and shutil.disk_usage(root).free < max(q['free'], q['initial_free'] if initial else 0) + extra:
                raise Blocked('combined free space/headroom')
        usage[category] = usage.get(category, 0) + extra
        for key, cap in q['caps'].items():
            if usage.get(key, 0) > cap: raise Blocked('combined partition '+key)
        data = sum(v for k,v in usage.items() if k.startswith(('PRIMARY:', 'REPLAY:')))
        logs = usage.get('core', 0) + usage.get('receipts', 0)
        if data > q['data_both'] or logs > q['logs'] or data+logs > q['all_artifacts']:
            raise Blocked('combined artifact quota')
        if usage.get('raw', 0) > self.c['limits']['retained_bytes']:
            raise Blocked('retained raw quota')
        return usage
