"""Packages the arena submission into IdeaForge_Arena.zip.

Layout:
    STRATEGY.pdf          the one-page strategy note required at the whistle
    STRATEGY.md           its markdown source
    ARENA_README.md        full narrative documentation (method, diagrams, numbers)
    code/
        agent.py            the agent exactly as deployed
        lib.py              parsing, forensics, fit scoring (pure, no network)
        arena_client.py     the kit's HTTP client, unmodified
        config.json         the exact config in effect at the close of the arena
        test_lib.py         the unit tests it was validated against
        mock_arena.py       the local mock server used for pre-deploy testing

Excludes local-only runtime artefacts: checkpoint.json, arena_log.jsonl,
agent.heartbeat, __pycache__, and the pdf build helpers.
"""
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "IdeaForge_Arena.zip")

TOP_LEVEL = ["STRATEGY.pdf", "STRATEGY.md", "ARENA_README.md"]
CODE = ["agent.py", "lib.py", "arena_client.py", "config.json", "test_lib.py", "mock_arena.py"]

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for name in TOP_LEVEL:
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            z.write(path, arcname=name)
        else:
            print("WARNING: missing", name)
    for name in CODE:
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            z.write(path, arcname=f"code/{name}")
        else:
            print("WARNING: missing", name)

print("written", OUT, round(os.path.getsize(OUT) / 1024, 1), "KB")
with zipfile.ZipFile(OUT) as z:
    for n in z.namelist():
        print(" ", n)
