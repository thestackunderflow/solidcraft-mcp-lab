#!/bin/bash
# Inside the beginner image: the shim and driver unit tests, then the app tests (app + window + bridged MCP). Log to tests/<phase>.log.
cd /work/tests && python3 -m pytest -v -p no:cacheprovider test_shim.py test_session.py test_beginner.py 2>&1 | tee "/work/tests/${PHASE:-run}-phase.log" | tail -25
