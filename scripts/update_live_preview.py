"""Refresh the local preview from the accepted public live-pilot audit only."""
from pathlib import Path
from civiclab.live_summary_viewer import build

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    print(build(root, root / 'data/processed/dashboard'))
