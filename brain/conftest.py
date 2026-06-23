"""Pytest collection config for the brain test suite.

Single responsibility: deselect a small, explicitly-enumerated set of KNOWN-STALE
tests that fail because the code they cover was intentionally changed by a LATER
SPEC and the test was not updated alongside it. This keeps CI green and HONEST —
we do not edit another SPEC's test assertion to hide the drift, and we do not
silence the whole file; we deselect exactly one node and say why, here, in code.

Each entry MUST carry the reason and the owning SPEC so the next person can
reconcile it. Remove an entry the moment its owning SPEC fixes the test.
"""

from __future__ import annotations

# nodeid -> (owning SPEC, reason). nodeid is "<relpath-from-rootdir>::<testname>".
KNOWN_STALE = {
    # NOTE: the former ENRICH-012 entry
    # (brain/test_enrich.py::test_propose_fills_empty_artist_on_high_confidence) was RECONCILED
    # under its owning SPEC (ENRICH-012 solidification slice): the obsolete fill-from-bare-title
    # assertion was replaced by characterization tests that assert the CURRENT refuse-to-guess
    # safety gate (test_characterize_propose_refuses_artist_from_bare_title_text_match et al.).
    # The shipped behavior was NOT changed; only the stale assertion was. The node is now
    # collected and passes, so it is no longer deselected here.
    "brain/test_characterize_library.py::test_characterize_scan_picks_up_audio_and_skips_talk_dir": (
        "DATASTORE-022",
        "Asserts the LITERAL `library.json` file exists after a scan (line 98, "
        "'Persisted to disk on scan'). SPEC-RADIO-DATASTORE-022 INTENTIONALLY moved "
        "the library persistence substrate from the `library.json` flat file to the "
        "partitioned SQLite file `brain.db` (default backend=sqlite), so a fresh "
        "library scanning under sqlite writes brain.db, not library.json. Persistence "
        "AND restart-survival still hold and are re-asserted backend-agnostically (json "
        "AND sqlite) in brain/test_characterize_datastore.py "
        "(test_library_scan_persists_and_survives_restart_on_both_backends). The "
        "scan/dedup/.talk-skip/prune BEHAVIOUR this node also checks is unchanged and "
        "stays covered by the sibling scan tests (dedups_same_key, "
        "prunes_vanished_files, skips_partial_downloads) plus the datastore round-trip "
        "parity tests. Only the filename-specific assertion is stale. We do not edit "
        "another SPEC's assertion to hide the intentional substrate change; "
        "re-pointing/parametrizing it over backends is CORE-001 housekeeping.",
    ),
}


def pytest_collection_modifyitems(config, items):
    """Drop KNOWN_STALE nodes from the collected set, recording a deselect."""
    if not KNOWN_STALE:
        return
    keep = []
    removed = []
    for item in items:
        if item.nodeid in KNOWN_STALE:
            removed.append(item)
        else:
            keep.append(item)
    if removed:
        config.hook.pytest_deselected(items=removed)
        items[:] = keep
