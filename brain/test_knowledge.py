"""Offline self-checks for KNOWLEDGE-008 (brain/knowledge.py + brain/research.py).

Run: python3 -m pytest brain/test_knowledge.py -q
 or: python3 brain/test_knowledge.py   (no pytest needed — a tiny runner is built in)

NO network, NO librosa/torch, NO live providers: the store is driven directly via its
insert APIs, and the research worker's providers are MONKEYPATCHED to return canned items
(mirrors test_metadata_u3.py's offline, provider-stubbed style). Every check runs against a
SQLite DB in a temp dir, so nothing touches the live /db.

Coverage (the 7 required self-checks):
  1. schema init in WAL mode on a temp dir
  2. insert entity + fact with provenance + as-of
  3. consensus: single verified source = qualified; >=2 verified sources = certain (KS-006)
  4. freshness gate rejects an expired time-sensitive fact AND a non-consensus fact-as-certain
     (KF-003)
  5. graph related-query returns only real edges (KG-003/004)
  6. grounding feed returns the expected shape and is empty-safe when the KB has nothing
     (KI-001)
  7. the KI-004 worked scenario assembles from stored rows (in-window certain + expired drop)
Plus: classify_consensus conflicting case (B-7 F3), and the Researcher fill path with stubbed
providers (idempotent, dated, sourced — B-2).
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta

# Allow `python3 brain/test_knowledge.py` from the repo root.
try:
    from brain import knowledge as K
    from brain import research as R
    from brain.library import Library, Track, normalize_key
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import knowledge as K
    from brain import research as R
    from brain.library import Library, Track, normalize_key


def _store(tmp: str) -> K.KnowledgeStore:
    return K.KnowledgeStore(os.path.join(tmp, "knowledge.db"), min_consensus_sources=2)


# ---------------------------------------------------------------------------
# 1. schema init in WAL mode on a temp dir
# ---------------------------------------------------------------------------
def test_schema_init_wal_mode():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        # The db file exists and survives (close + reopen = same contents).
        assert os.path.exists(os.path.join(tmp, "knowledge.db"))
        cur = st._conn.cursor()
        mode = cur.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal", f"journal_mode is {mode}, expected wal"
        fk = cur.execute("PRAGMA foreign_keys").fetchone()[0]
        assert int(fk) == 1, "foreign_keys must be ON"
        # schema_version recorded.
        sv = cur.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        assert int(sv) == K.SCHEMA_VERSION
        st.close()
        # Reopen: contents intact (survives a restart).
        st2 = _store(tmp)
        assert st2.stats()["schema_version"] == K.SCHEMA_VERSION
        st2.close()


# ---------------------------------------------------------------------------
# 2. insert entity + fact with provenance + as-of  (and rejection of un-sourced/undated)
# ---------------------------------------------------------------------------
def test_entity_and_fact_with_provenance():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        nk = normalize_key("Aphex Twin", "")
        eid = st.upsert_entity(K.ENTITY_ARTIST, "Aphex Twin", norm_key=nk, lib_key=nk)
        assert eid > 0
        # upsert is idempotent — same (etype, norm_key) returns the same id.
        eid2 = st.upsert_entity(K.ENTITY_ARTIST, "Aphex Twin", norm_key=nk)
        assert eid2 == eid

        fid = st.add_fact(
            eid, "origin", "Limerick, Ireland",
            kind=K.KIND_TIMELESS,
            sources=[(K.SRC_MUSICBRAINZ, "https://musicbrainz.org/artist/x")],
            as_of="2026-06-22",
        )
        assert fid is not None
        facts = st.facts_for(eid)
        assert len(facts) == 1
        f = facts[0]
        assert f["value"] == "Limerick, Ireland"
        assert f["as_of"] == "2026-06-22"
        assert f["sources"] and f["sources"][0]["source"] == K.SRC_MUSICBRAINZ
        assert f["sources"][0]["url"].startswith("https://")

        # [HARD KS-003] an un-sourced claim is REJECTED (not stored as trusted).
        rej = st.add_fact(eid, "rumour", "secret album", kind=K.KIND_TIMELESS, sources=[])
        assert rej is None
        assert len(st.facts_for(eid)) == 1  # unchanged
        st.close()


# ---------------------------------------------------------------------------
# 3. consensus: single verified source = qualified; >=2 verified = certain  (KS-006)
# ---------------------------------------------------------------------------
def test_consensus_single_vs_multi_source():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        nk = normalize_key("Band X", "")
        eid = st.upsert_entity(K.ENTITY_ARTIST, "Band X", norm_key=nk)

        # F1: founded — asserted by MusicBrainz AND Wikidata AND Wikipedia -> consensus-passed.
        f1 = st.add_fact(
            eid, "founded", "1994",
            kind=K.KIND_TIMELESS,
            sources=[
                (K.SRC_MUSICBRAINZ, "https://musicbrainz.org/a"),
                (K.SRC_WIKIDATA, "https://www.wikidata.org/a"),
                (K.SRC_WIKIPEDIA, "https://en.wikipedia.org/a"),
            ],
            as_of="2026-06-22",
        )
        # F2: single web-press source -> single (qualified), never certain.
        f2 = st.add_fact(
            eid, "signed", "Label Y",
            kind=K.KIND_TIMELESS,
            sources=[(K.SRC_PRESS, "https://pitchfork.example/a")],
            as_of="2026-06-22",
        )
        facts = {f["predicate"]: f for f in st.facts_for(eid)}
        assert facts["founded"]["consensus"] == K.CONSENSUS_PASSED, facts["founded"]
        assert facts["founded"]["confidence"] > 0.5
        assert facts["signed"]["consensus"] == K.CONSENSUS_SINGLE, facts["signed"]
        assert f1 is not None and f2 is not None

        # A non-allowlisted source does NOT count toward consensus.
        eid2 = st.upsert_entity(K.ENTITY_ARTIST, "Band Z", norm_key=normalize_key("Band Z", ""))
        st.add_fact(
            eid2, "claim", "v",
            kind=K.KIND_TIMELESS,
            sources=[("fan-wiki", "https://fandom.example"),
                     ("fan-wiki2", "https://fandom2.example")],
            as_of="2026-06-22",
        )
        fz = st.facts_for(eid2)[0]
        assert fz["consensus"] == K.CONSENSUS_SINGLE, fz  # no verified backing -> not passed
        st.close()


def test_classify_consensus_conflicting():
    # B-7 F3: verified sources disagree (Wikipedia 1971 vs Last.fm 1972); fan-wiki ignored.
    vs = {
        "1971": {K.SRC_WIKIPEDIA},
        "1972": {K.SRC_LASTFM},
        "1973": {"fan-wiki"},  # not on the allowlist — dropped entirely
    }
    out = K.classify_consensus(vs, min_sources=2)
    assert "1973" not in out  # non-allowlisted value has no verified backing
    assert out["1971"]["consensus"] == K.CONSENSUS_CONFLICTING, out
    assert out["1972"]["consensus"] == K.CONSENSUS_CONFLICTING, out


# ---------------------------------------------------------------------------
# 4. freshness gate rejects expired time-sensitive AND non-consensus-as-certain  (KF-003)
# ---------------------------------------------------------------------------
def test_freshness_gate():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        nk = normalize_key("Artist", "")
        eid = st.upsert_entity(K.ENTITY_ARTIST, "Artist", norm_key=nk)

        # A time-sensitive, CONSENSUS-PASSED upcoming-release fact valid until 2026-07-06.
        st.add_fact(
            eid, "upcoming_release", "album on Label X",
            kind=K.KIND_TIME_SENSITIVE,
            sources=[(K.SRC_MUSICBRAINZ, "https://mb/x"), (K.SRC_PRESS, "https://press/x")],
            as_of="2026-06-22", valid_until="2026-07-06",
        )
        fact = st.facts_for(eid)[0]
        assert fact["consensus"] == K.CONSENSUS_PASSED

        # In-window (2026-06-22) AND consensus-passed -> certain.
        assert K.KnowledgeStore.fact_status(fact, date(2026, 6, 22)) == "certain"
        # Past the window (2026-07-20) -> stale (dropped), even though consensus-passed.
        assert K.KnowledgeStore.fact_status(fact, date(2026, 7, 20)) == "stale"

        # A non-stale but SINGLE-source fact is qualified, never certain.
        st.add_fact(
            eid, "tour", "current tour",
            kind=K.KIND_TIME_SENSITIVE,
            sources=[(K.SRC_PRESS, "https://press/tour")],
            as_of="2026-06-22", valid_until="2026-12-31",
        )
        tour = [f for f in st.facts_for(eid) if f["predicate"] == "tour"][0]
        assert K.KnowledgeStore.fact_status(tour, date(2026, 6, 22)) == "qualified"

        # facts_due_for_refresh: a time-sensitive fact older than the tight threshold flags;
        # a timeless fact within the long threshold does not.
        st.add_fact(eid, "founded", "1994", kind=K.KIND_TIMELESS,
                    sources=[(K.SRC_MUSICBRAINZ, "https://mb/f")], as_of="2026-06-22")
        old = (date(2026, 6, 22) - timedelta(days=10)).isoformat()
        st.add_fact(eid, "stale_news", "v", kind=K.KIND_TIME_SENSITIVE,
                    sources=[(K.SRC_PRESS, "https://p")], as_of=old, valid_until="2030-01-01")
        due = st.facts_due_for_refresh(
            today=date(2026, 6, 22), time_sensitive_days=3, timeless_days=180
        )
        preds = {d["predicate"] for d in due}
        assert "stale_news" in preds            # time-sensitive, 10 days old > 3-day threshold
        assert "founded" not in preds           # timeless, within 180-day threshold
        st.close()


# ---------------------------------------------------------------------------
# 5. graph related-query returns only real edges  (KG-003/004)
# ---------------------------------------------------------------------------
def test_graph_real_edges_only():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        band = st.upsert_entity(K.ENTITY_ARTIST, "Band B", norm_key=normalize_key("Band B", ""))
        member = st.upsert_entity(K.ENTITY_ARTIST, "Artist A", norm_key=normalize_key("Artist A", ""))
        # An UNRELATED artist with NO edge to Band B — must never be returned as related.
        st.upsert_entity(K.ENTITY_ARTIST, "Stranger C", norm_key=normalize_key("Stranger C", ""))

        st.add_edge(band, member, K.REL_MEMBER_OF, provenance=K.EDGE_RESEARCH,
                    source=K.SRC_MUSICBRAINZ, url="https://mb/rel")
        related = st.related_entities(band)
        names = {e["dst_name"] for e in related}
        assert "Artist A" in names
        assert "Stranger C" not in names  # no edge -> not related (NFR-K-6)
        # The edge carries type + provenance + as-of (KG-001).
        edge = related[0]
        assert edge["rel"] == K.REL_MEMBER_OF
        assert edge["provenance"] == K.EDGE_RESEARCH
        assert edge["as_of"]
        st.close()


# ---------------------------------------------------------------------------
# 6. grounding feed shape + empty-safe  (KI-001)
# ---------------------------------------------------------------------------
def test_grounding_feed_shape_and_empty_safe():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        # Empty-safe: an unresearched artist yields empty lists (Scenario B-6).
        empty = st.grounding_for_artist(normalize_key("Nobody", ""))
        assert empty == {"artist": "", "grounded_facts": [], "grounded_relations": []}

        nk = normalize_key("Artist", "")
        eid = st.upsert_entity(K.ENTITY_ARTIST, "Artist", norm_key=nk)
        st.add_fact(eid, "founded", "1994", kind=K.KIND_TIMELESS,
                    sources=[(K.SRC_MUSICBRAINZ, "https://mb/a"),
                             (K.SRC_WIKIDATA, "https://wd/a")], as_of="2026-06-22")
        st.add_fact(eid, "rumoured", "supergroup", kind=K.KIND_TIMELESS,
                    sources=[(K.SRC_PRESS, "https://press/a")], as_of="2026-06-22")
        proj = st.upsert_entity(K.ENTITY_ARTIST, "Side P", norm_key=normalize_key("Side P", ""))
        st.add_edge(eid, proj, K.REL_SIDE_PROJECT, provenance=K.EDGE_RESEARCH)

        g = st.grounding_for_artist(nk, today=date(2026, 6, 22))
        assert g["artist"] == "Artist"
        by_pred = {f["predicate"]: f for f in g["grounded_facts"]}
        # consensus-passed fact -> certain, no hedge.
        assert by_pred["founded"]["certain"] is True
        assert by_pred["founded"]["hedge"] == ""
        # single-source fact -> qualified, carries a hedge.
        assert by_pred["rumoured"]["certain"] is False
        assert by_pred["rumoured"]["hedge"]
        # relation is a real edge.
        assert g["grounded_relations"][0]["rel"] == K.REL_SIDE_PROJECT
        assert g["grounded_relations"][0]["target"] == "Side P"
        st.close()


# ---------------------------------------------------------------------------
# 7. the KI-004 worked scenario assembles from stored rows
# ---------------------------------------------------------------------------
def test_ki004_worked_scenario():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        # ARTIST with a side-project; the side-project has a latest single in the library.
        artist = st.upsert_entity(K.ENTITY_ARTIST, "%ARTIST%",
                                  norm_key=normalize_key("%ARTIST%", ""))
        solo = st.upsert_entity(K.ENTITY_ARTIST, "%SOLO%",
                                norm_key=normalize_key("%SOLO%", ""), lib_key=None)
        st.add_edge(artist, solo, K.REL_SIDE_PROJECT, provenance=K.EDGE_RESEARCH,
                    source=K.SRC_MUSICBRAINZ, url="https://mb/sp")

        # A TIME-SENSITIVE, sourced, dated, CONSENSUS-PASSED release fact on the solo project.
        st.add_fact(
            solo, "upcoming_release", "new album on %LABEL%",
            kind=K.KIND_TIME_SENSITIVE,
            sources=[(K.SRC_MUSICBRAINZ, "https://mb/rel"), (K.SRC_OFFICIAL, "https://label/rel")],
            as_of="2026-06-22", valid_until="2026-07-06",
        )

        # The library holds the solo project's latest single (attaches by normalize_key).
        single_key = normalize_key("%SOLO%", "Latest Single")
        lib_index = os.path.join(tmp, "library.json")
        lib = Library(tmp, lib_index)
        lib._tracks[single_key] = Track(
            path=os.path.join(tmp, "single.mp3"), artist="%SOLO%", title="Latest Single",
            key=single_key,
        )

        # IN-WINDOW (2026-06-22): the release fact is CERTAIN; the side-project edge is real;
        # the single resolves in the library -> the worked sentence composes + the single
        # can be queued.
        g = st.grounding_for_artist(normalize_key("%ARTIST%", ""), today=date(2026, 6, 22))
        rel = g["grounded_relations"][0]
        assert rel["rel"] == K.REL_SIDE_PROJECT and rel["target"] == "%SOLO%"
        # the solo project's grounded release fact, in-window + consensus-passed = certain.
        gsolo = st.grounding_for_artist(normalize_key("%SOLO%", ""), today=date(2026, 6, 22))
        rel_fact = [f for f in gsolo["grounded_facts"] if f["predicate"] == "upcoming_release"][0]
        assert rel_fact["certain"] is True
        assert "%LABEL%" in rel_fact["value"]
        # curation action: the latest single is resolvable + airable in the library.
        assert lib.has_key(single_key)

        # EXPIRED (2026-07-20): the "in two weeks" framing is gated out (dropped).
        gsolo_expired = st.grounding_for_artist(normalize_key("%SOLO%", ""), today=date(2026, 7, 20))
        assert not [f for f in gsolo_expired["grounded_facts"]
                    if f["predicate"] == "upcoming_release"], "expired release must be dropped"
        st.close()


# ---------------------------------------------------------------------------
# Bonus: Researcher fill path with stubbed providers (B-2: dated, sourced, idempotent)
# ---------------------------------------------------------------------------
class _FakeCfg:
    knowledge_enabled = True
    knowledge_research_interval_seconds = 60
    knowledge_research_batch = 5
    knowledge_max_concurrent_downloads = 1
    knowledge_http_timeout_seconds = 10
    knowledge_min_consensus_sources = 2
    knowledge_default_window_days = 30
    knowledge_refresh_time_sensitive_days = 3
    knowledge_refresh_timeless_days = 180
    lastfm_api_key = ""
    musicbrainz_user_agent = "GoldenShowerRadio/1.0 (test)"


class _FakeState:
    def downloading(self):
        return []  # nothing downloading -> throttle open


def test_researcher_fill_path_stubbed():
    import threading

    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        lib = Library(tmp, os.path.join(tmp, "library.json"))
        k = normalize_key("Boards of Canada", "Roygbiv")
        lib._tracks[k] = Track(path=os.path.join(tmp, "x.mp3"),
                               artist="Boards of Canada", title="Roygbiv",
                               key=k, genre="IDM")

        worker = R.Researcher(_FakeCfg(), lib, st, _FakeState(), threading.Event())

        # Stub the external providers with canned, dated, sourced items (no network).
        def fake_mb(artist):
            return [{"type": "fact", "predicate": "formed", "value": "1986",
                     "kind": K.KIND_TIMELESS,
                     "sources": [(K.SRC_MUSICBRAINZ, "https://mb/boc")]},
                    {"type": "edge", "rel": K.REL_MEMBER_OF, "target": "Michael Sandison",
                     "target_type": K.ENTITY_PERSON, "source": K.SRC_MUSICBRAINZ,
                     "url": "https://mb/boc/rel"}]

        def fake_wd(artist):
            return [{"type": "fact", "predicate": "formed", "value": "1986",
                     "kind": K.KIND_TIMELESS,
                     "sources": [(K.SRC_WIKIDATA, "https://wd/boc")]}]

        worker._provider_musicbrainz = fake_mb  # type: ignore[assignment]
        worker._provider_wikidata = fake_wd     # type: ignore[assignment]
        # wikipedia/lastfm/web stay as the real graceful-empty seams (return []).

        worker._tick()
        ent = st.get_entity(K.ENTITY_ARTIST, normalize_key("Boards of Canada", ""))
        assert ent is not None
        eid = ent["id"]
        facts = {f["predicate"]: f for f in st.facts_for(eid)}
        # "formed" corroborated by MusicBrainz + Wikidata -> consensus-passed (certain).
        assert facts["formed"]["consensus"] == K.CONSENSUS_PASSED, facts["formed"]
        # a member-of edge was written (research-provenance).
        edges = st.edges_from(eid)
        rels = {e["rel"] for e in edges}
        assert K.REL_MEMBER_OF in rels
        # a seed genre edge was created from the library's IDM dimension.
        assert K.REL_GENRE in rels
        # IDEMPOTENT: a 2nd tick adds no duplicate facts/edges.
        n_facts = len(st.facts_for(eid))
        n_edges = len(st.edges_from(eid))
        worker._tick()
        assert len(st.facts_for(eid)) == n_facts, "facts duplicated on re-run"
        assert len(st.edges_from(eid)) == n_edges, "edges duplicated on re-run"
        st.close()


# ---------------------------------------------------------------------------
# v0.3.0 tests — KS-007/008/009, KF-005, KR-006/007/008, KG-006, KI-006
# ---------------------------------------------------------------------------

# KS-007 — per-track editorial fields
def test_ks007_track_editorial_fields():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        eid = st.upsert_entity(K.ENTITY_SONG, "Song A", norm_key=normalize_key("artist", "Song A"))

        # lyrical_meaning is plural-capable: two distinct interpretations stored separately.
        fid1 = st.add_track_editorial(
            eid, K.PRED_LYRICAL_MEANING, "interpretation of loss",
            [(K.SRC_PRESS, "https://press/a")],
        )
        fid2 = st.add_track_editorial(
            eid, K.PRED_LYRICAL_MEANING, "metaphor for exile",
            [(K.SRC_OFFICIAL, "https://official/a")],
        )
        assert fid1 is not None and fid2 is not None
        assert fid1 != fid2, "each lyrical_meaning interpretation must be a distinct row"

        # Other editorial fields work too.
        fid3 = st.add_track_editorial(
            eid, K.PRED_PRODUCTION_NOTES, "recorded on 8-track in 1992",
            [(K.SRC_PRESS, "https://press/b")],
        )
        assert fid3 is not None

        # Kind must be CONTEXTUAL (never date-expired).
        facts = {f["predicate"]: f for f in st.facts_for(eid) if f["predicate"] == K.PRED_PRODUCTION_NOTES}
        assert facts[K.PRED_PRODUCTION_NOTES]["kind"] == K.TEMPORALITY_CONTEXTUAL

        # Unknown field raises.
        try:
            st.add_track_editorial(eid, "bad_field", "v", [(K.SRC_PRESS, "https://p")])
            assert False, "expected ValueError"
        except ValueError:
            pass
        st.close()


# KS-008 — subjectivity class + confidence grade + disagreement
def test_ks008_subjectivity_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        eid = st.upsert_entity(K.ENTITY_ARTIST, "Artist K", norm_key=normalize_key("Artist K", ""))

        # FACTUAL by default (backward compat).
        fid = st.add_fact(eid, "hometown", "Glasgow",
                          kind=K.KIND_TIMELESS,
                          sources=[(K.SRC_MUSICBRAINZ, "https://mb/k"),
                                   (K.SRC_WIKIDATA, "https://wd/k")],
                          as_of="2026-06-22")
        assert fid is not None
        f = st.facts_for(eid)[0]
        assert f.get("subjectivity_class") == K.SUBJECTIVITY_FACTUAL

        # EDITORIAL_OPINION + GRADE_MODERATE stored and retrieved.
        eid2 = st.upsert_entity(K.ENTITY_ARTIST, "Artist L",
                                norm_key=normalize_key("Artist L", ""))
        fid2 = st.add_fact(
            eid2, "genre_feel", "post-punk adjacent",
            kind=K.KIND_TIMELESS,
            sources=[(K.SRC_PITCHFORK, "https://pf/l")],
            as_of="2026-06-22",
            subjectivity_class=K.SUBJECTIVITY_EDITORIAL_OPINION,
            confidence_grade=K.GRADE_MODERATE,
            disagreement="some say industrial",
        )
        assert fid2 is not None
        f2 = st.facts_for(eid2)[0]
        assert f2["subjectivity_class"] == K.SUBJECTIVITY_EDITORIAL_OPINION
        assert f2["confidence_grade"] == K.GRADE_MODERATE
        assert f2["disagreement"] == "some say industrial"

        # grounding_for_artist includes subjectivity_class + confidence_grade.
        g = st.grounding_for_artist(normalize_key("Artist L", ""), today=date(2026, 6, 22))
        gf = g["grounded_facts"][0]
        assert gf["subjectivity_class"] == K.SUBJECTIVITY_EDITORIAL_OPINION
        assert gf["confidence_grade"] == K.GRADE_MODERATE
        st.close()


# KS-009 — reliability-ranked source tiers
def test_ks009_source_tiers():
    # Verify tier membership.
    assert K.SOURCE_TIERS[K.SRC_MUSICBRAINZ] == K.TIER_AUTHORITATIVE_STRUCTURED
    assert K.SOURCE_TIERS[K.SRC_DISCOGS] == K.TIER_AUTHORITATIVE_STRUCTURED
    assert K.SOURCE_TIERS[K.SRC_GUARDIAN] == K.TIER_REPUTABLE_PRESS
    assert K.SOURCE_TIERS[K.SRC_PITCHFORK] == K.TIER_REPUTABLE_PRESS
    assert K.SOURCE_TIERS[K.SRC_AQUARIUM_DRUNKARD] == K.TIER_EDITORIAL_BLOG
    assert K.SOURCE_TIERS[K.SRC_BANDCAMP_DAILY] == K.TIER_EDITORIAL_BLOG
    assert K.SOURCE_TIERS[K.SRC_WHOSAMPLED] == K.TIER_EDITORIAL_BLOG
    assert K.SOURCE_TIERS[K.SRC_LASTFM] == K.TIER_CROWD

    # AUTHORITATIVE_STRUCTURED sources must have higher weight than EDITORIAL_BLOG.
    assert K.SOURCE_WEIGHTS[K.SRC_MUSICBRAINZ] > K.SOURCE_WEIGHTS[K.SRC_AQUARIUM_DRUNKARD]
    # All expected sources are in SOURCE_WEIGHTS.
    for src in (K.SRC_GUARDIAN, K.SRC_BBC, K.SRC_PITCHFORK, K.SRC_STEREOGUM,
                K.SRC_AQUARIUM_DRUNKARD, K.SRC_BANDCAMP_DAILY, K.SRC_WHOSAMPLED,
                K.SRC_DISCOGS):
        assert src in K.SOURCE_WEIGHTS, f"{src} missing from SOURCE_WEIGHTS"


# KF-005 — CONTEXTUAL currency class
def test_kf005_contextual_never_stale():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        eid = st.upsert_entity(K.ENTITY_SONG, "Song B", norm_key=normalize_key("artist", "song b"))

        # Contextual fact stored far in the past — should NOT be stale.
        old_date = (date(2026, 6, 22) - timedelta(days=3000)).isoformat()
        fid = st.add_fact(eid, K.PRED_WRITING_STORY, "written during a breakup",
                          kind=K.TEMPORALITY_CONTEXTUAL,
                          sources=[(K.SRC_PRESS, "https://press/b")],
                          as_of=old_date)
        assert fid is not None
        fact = [f for f in st.facts_for(eid) if f["predicate"] == K.PRED_WRITING_STORY][0]
        assert fact["kind"] == K.TEMPORALITY_CONTEXTUAL

        # fact_status must never return "stale" for contextual, even years later.
        status = K.KnowledgeStore.fact_status(fact, date(2026, 6, 22))
        assert status != "stale", f"CONTEXTUAL fact must not be stale; got {status!r}"
        # It IS qualified (single source), not certain.
        assert status == "qualified"

        # facts_due_for_refresh: contextual uses the TIMELESS window.
        # Store a contextual fact with a very old as-of that exceeds timeless_days=180.
        # It SHOULD appear in the refresh list (old but not expired).
        very_old = (date(2026, 6, 22) - timedelta(days=200)).isoformat()
        fid2 = st.add_fact(eid, K.PRED_ERA_CONTEXT, "90s UK rave scene",
                           kind=K.TEMPORALITY_CONTEXTUAL,
                           sources=[(K.SRC_PRESS, "https://p2")],
                           as_of=very_old)
        assert fid2 is not None
        due = st.facts_due_for_refresh(
            today=date(2026, 6, 22), time_sensitive_days=3, timeless_days=180
        )
        preds = {d["predicate"] for d in due}
        assert K.PRED_ERA_CONTEXT in preds, "old contextual fact should be due for refresh"
        # The writing_story (3000 days old) should also appear.
        assert K.PRED_WRITING_STORY in preds
        st.close()


# KR-006 + KR-007 — research job queue
def test_kr006_research_jobs():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        eid = st.upsert_entity(K.ENTITY_ARTIST, "Research A",
                               norm_key=normalize_key("Research A", ""))

        # Enqueue an artist job.
        jid = st.enqueue_research(eid, K.JOB_ARTIST, metadata={"source": "mb"})
        assert jid > 0

        # Mark complete.
        st.mark_research_complete(jid)

        # Enqueue a preshow batch.
        eid2 = st.upsert_entity(K.ENTITY_ARTIST, "Research B",
                                norm_key=normalize_key("Research B", ""))
        eid3 = st.upsert_entity(K.ENTITY_ARTIST, "Research C",
                                norm_key=normalize_key("Research C", ""))
        jids = st.enqueue_preshow_research([eid2, eid3], timeout_seconds=120.0)
        assert len(jids) == 2
        assert all(j > 0 for j in jids), f"all job ids must be positive: {jids}"

        # Mark one preshow job as errored.
        st.mark_research_complete(jids[0], error="provider timeout")

        # Verify rows exist in the DB.
        with st._lock:
            cur = st._conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM research_jobs")
            n = cur.fetchone()["n"]
        assert n >= 3, f"expected at least 3 research_jobs rows, got {n}"
        st.close()


# KR-008 — Discogs free-text notes always hedged
def test_kr008_discogs_free_text_capped():
    # is_discogs_free_text() helper.
    assert K.is_discogs_free_text(K.SRC_DISCOGS, "discogs_notes") is True
    assert K.is_discogs_free_text(K.SRC_DISCOGS, "release_notes") is True
    assert K.is_discogs_free_text(K.SRC_DISCOGS, "description") is True
    assert K.is_discogs_free_text(K.SRC_DISCOGS, "track_listing") is False  # structured
    assert K.is_discogs_free_text(K.SRC_MUSICBRAINZ, "discogs_notes") is False  # wrong src

    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        eid = st.upsert_entity(K.ENTITY_RELEASE, "Album Z",
                               norm_key=normalize_key("", "Album Z"))

        # Two Discogs sources agreeing on a free-text notes predicate must NOT reach PASSED.
        st.add_fact(eid, "discogs_notes", "great album from the 90s",
                    kind=K.KIND_TIMELESS,
                    sources=[(K.SRC_DISCOGS, "https://discogs.com/a"),
                             (K.SRC_DISCOGS, "https://discogs.com/b")],
                    as_of="2026-06-22")
        # Since add_fact applies the Discogs check on the FIRST source only, and
        # _recompute_consensus caps Discogs-only agreement at SINGLE, we check consensus.
        fact = [f for f in st.facts_for(eid) if f["predicate"] == "discogs_notes"][0]
        assert fact["consensus"] != K.CONSENSUS_PASSED, (
            "Discogs-only free-text should never reach CONSENSUS_PASSED"
        )

        # Structured Discogs fact + MusicBrainz CAN reach consensus.
        st.add_fact(eid, "release_date", "1994-03-02",
                    kind=K.KIND_TIMELESS,
                    sources=[(K.SRC_DISCOGS, "https://discogs.com/c"),
                             (K.SRC_MUSICBRAINZ, "https://mb/c")],
                    as_of="2026-06-22")
        rd_fact = [f for f in st.facts_for(eid) if f["predicate"] == "release_date"][0]
        # "release_date" is not a free-text predicate; Discogs+MB can yield PASSED.
        assert rd_fact["consensus"] == K.CONSENSUS_PASSED, (
            "Discogs+MusicBrainz structured fact should reach CONSENSUS_PASSED"
        )
        st.close()


# KG-006 — richer track-to-track edge types + ENTITY_PERSON/ENTITY_PLACE
def test_kg006_richer_edges():
    # New relationship constants exist.
    assert hasattr(K, "REL_COVER")
    assert hasattr(K, "REL_SAMPLE")
    assert hasattr(K, "REL_WRITING_CONNECTION")
    assert hasattr(K, "REL_THEMATIC_INFLUENCE")
    # New entity type constants exist.
    assert K.ENTITY_PERSON == "person"
    assert K.ENTITY_PLACE == "place"
    # VALID_RELS contains all expected types.
    for rel in (K.REL_COVER, K.REL_SAMPLE, K.REL_WRITING_CONNECTION,
                K.REL_THEMATIC_INFLUENCE, K.REL_MEMBER_OF, K.REL_RELEASED_ON):
        assert rel in K.VALID_RELS, f"{rel} not in VALID_RELS"

    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)
        song_a = st.upsert_entity(K.ENTITY_SONG, "Song A",
                                  norm_key=normalize_key("artist_a", "song_a"))
        song_b = st.upsert_entity(K.ENTITY_SONG, "Song B",
                                  norm_key=normalize_key("artist_b", "song_b"))
        person = st.upsert_entity(K.ENTITY_PERSON, "A Songwriter",
                                  norm_key=normalize_key("a songwriter", ""))
        place = st.upsert_entity(K.ENTITY_PLACE, "Glasgow",
                                 norm_key=normalize_key("glasgow", ""))

        # Cover + sample edges between songs.
        eid1 = st.add_edge(song_b, song_a, K.REL_COVER, provenance=K.EDGE_RESEARCH,
                           source=K.SRC_MUSICBRAINZ, url="https://mb/cover")
        eid2 = st.add_edge(song_a, song_b, K.REL_THEMATIC_INFLUENCE,
                           provenance=K.EDGE_RESEARCH)
        assert eid1 is not None and eid2 is not None

        # ENTITY_PERSON and ENTITY_PLACE are valid entity types.
        assert person > 0 and place > 0

        # WRITING_CONNECTION person edge.
        eid3 = st.add_edge(song_a, person, K.REL_WRITING_CONNECTION,
                           provenance=K.EDGE_RESEARCH)
        assert eid3 is not None
        edges = st.edges_from(song_a)
        rels = {e["rel"] for e in edges}
        assert K.REL_THEMATIC_INFLUENCE in rels
        assert K.REL_WRITING_CONNECTION in rels
        st.close()


# KI-006 — release-scoped grounding accessor
def test_ki006_grounding_for_release():
    with tempfile.TemporaryDirectory() as tmp:
        st = _store(tmp)

        # Miss: unknown release returns empty-safe dict, never raises.
        result = st.grounding_for_release("nobody", "unknown album", today=date(2026, 6, 22))
        assert result == {"has_facts": False, "release": {}, "tracks": [], "edges": []}

        # Build a release entity with facts.
        rel_eid = st.upsert_entity(K.ENTITY_RELEASE, "Test Album",
                                   norm_key=normalize_key("", "Test Album"))
        st.add_fact(rel_eid, "release_year", "1994", kind=K.KIND_TIMELESS,
                    sources=[(K.SRC_MUSICBRAINZ, "https://mb/ta"),
                             (K.SRC_WIKIDATA, "https://wd/ta")],
                    as_of="2026-06-22")

        # Build a track linked to this release via REL_RELEASED_ON (reverse edge).
        track_eid = st.upsert_entity(K.ENTITY_SONG, "Track 1",
                                     norm_key=normalize_key("artist", "track 1"))
        st.add_track_editorial(track_eid, K.PRED_PRODUCTION_NOTES,
                               "recorded at Rockfield",
                               [(K.SRC_PRESS, "https://press/t1")],
                               as_of="2026-06-22")
        # Track points at the release via REL_RELEASED_ON edge.
        st.add_edge(track_eid, rel_eid, K.REL_RELEASED_ON, provenance=K.EDGE_RESEARCH)

        # Add a credited_to edge from release to an entity.
        label_eid = st.upsert_entity(K.ENTITY_LABEL, "Warp Records",
                                     norm_key=normalize_key("warp records", ""))
        st.add_edge(rel_eid, label_eid, K.REL_SIGNED_TO, provenance=K.EDGE_RESEARCH)

        g = st.grounding_for_release("test artist", "Test Album", today=date(2026, 6, 22))
        assert g["has_facts"] is True
        assert "release_year" in g["release"]
        assert g["release"]["release_year"]["certain"] is True
        # Track facts appear in the tracks list.
        track_names = [t["name"] for t in g["tracks"]]
        assert "Track 1" in track_names
        track = next(t for t in g["tracks"] if t["name"] == "Track 1")
        assert K.PRED_PRODUCTION_NOTES in track["facts"]
        # Edges appear.
        edge_rels = {e["rel"] for e in g["edges"]}
        assert K.REL_SIGNED_TO in edge_rels
        st.close()


# ---------------------------------------------------------------------------
# tiny built-in runner (works with or without pytest)
# ---------------------------------------------------------------------------
def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run_all())
