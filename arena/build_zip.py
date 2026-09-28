"""Packages the deployable agent files into parakh_arena.zip.

Excludes local-only test artefacts (mock_arena.py, checkpoint.json,
arena_log.jsonl, run/mock logs, __pycache__) so the console upload contains
exactly what should run in the sandbox.
"""
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "parakh_arena.zip")
INCLUDE = ["agent.py", "lib.py", "arena_client.py", "config.json", "STRATEGY.md"]

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for name in INCLUDE:
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            z.write(path, arcname=name)
        else:
            print("WARNING: missing", name)

print("written", OUT, round(os.path.getsize(OUT) / 1024, 1), "KB")
with zipfile.ZipFile(OUT) as z:
    for n in z.namelist():
        print(" ", n)
