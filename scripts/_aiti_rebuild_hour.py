#!/usr/bin/env python3
"""Snapshot AITI named-processor source-lines, rebuild pages, restore if wiped."""
import json
import sys
from pathlib import Path

ROOT = Path("/workspace/trust-index")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from verify_empty_files import snapshot_aiti, restore_aiti, load_json, write_json, PUBLIC
import build_pages

public = load_json(PUBLIC, {})
snap = snapshot_aiti(public)
print(f"AITI snapshot rows={len(snap)}", flush=True)
rc = build_pages.main()
print(f"build_pages rc={rc}", flush=True)
public = load_json(PUBLIC, {})
dropped = restore_aiti(public, snap)
if dropped:
    write_json(PUBLIC, public)
print(f"DROPPED_INSTRUMENTS {dropped}", flush=True)
sys.exit(rc or 0)
