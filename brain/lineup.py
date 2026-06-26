"""SPEC-RADIO-LINEUP-050 — Weekly Lineup Grid, Hiatus State, Flagship Pin &
Cross-Persona Show Firewall (M1 + M2).

A THIN, ADDITIVE extension over the existing ShowEngine (``brain/shows.py``),
LifecycleEngine (``brain/lifecycle.py``), and ``Schedule.assign_persona()``
(``brain/schedule.py``). This module owns the durable recurring-slot show IDENTITY
and the cross-persona, cross-time similarity firewall. It runs no show, forks no
scheduler/ledger/clock, and re-owns no lifecycle FSM (NFR-LU-5).

This file ships M1 + M2 only:

  M1 (REQ-SH-001, NFR-LU-1/6) — the durable ``show_registry`` table in the
     DATASTORE-022 ``events.db`` partition + the ``ShowRegistry`` CRUD store. The
     store MIRRORS ``analytics.PlayEventsStore`` exactly: one shared connection +
     WAL write lock per ``events.db`` via the ``sqlite_store._conn_for`` registry
     (REQ-DP-003). Rows (incl. hiatus/discontinued/retired) are NEVER deleted —
     permanent programming memory + the firewall corpus.

  M2 (REQ-SQ-001/002/003, NFR-LU-2/4) — the cross-persona similarity firewall. A
     new recurring-show concept must be NOVEL against EVERY non-active row ACROSS
     ALL personas, REUSING the EXISTING ``shows.angle_similarity`` (token-set
     Jaccard, [0..1]) — no second metric. Over-threshold concepts are rejected and
     regenerated via the consumed ``ShowEngine.propose_show`` (bounded by
     ``shows_max_regenerate``); after the bound, the firewall ESCALATES (never loops,
     never binds a near-duplicate). A clean ``revet_reactivation`` entry point is
     exposed for the M4 hiatus state machine to call on long-hiatus reactivation.

Boundary discipline (spec.md §11 / plan D-LU-3): the cross-persona scan is injected
at THIS lineup layer; ``brain/shows.py`` and ``brain/lifecycle.py`` are consumed
unchanged.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .logging_setup import log_event
from .shows import angle_similarity

log = logging.getLogger("brain.lineup")


# --------------------------------------------------------------------------- #
# Lineup status vocabulary (the recurring-slot identity layer).
#
# ``active`` is the only status the firewall EXCLUDES from its scan corpus (a live
# show is not a duplicate target). ``hiatus``/``discontinued``/``retired`` are all
# "non-active" and form the permanent firewall memory. ``concept`` is the pre-vet
# staging state. NOTE: these are the LINEUP recurring-identity states; they do NOT
# redefine the SHOWS-020 per-persona ``Show.status`` (proposed/active/retired) nor
# the OPS-004 lifecycle FSM — LINEUP routes its terminal exit THROUGH those engines.
# --------------------------------------------------------------------------- #

LINEUP_CONCEPT = "concept"
LINEUP_ACTIVE = "active"
LINEUP_HIATUS = "hiatus"
LINEUP_DISCONTINUED = "discontinued"
LINEUP_RETIRED = "retired"

# The full column set of show_registry (REQ-SH-001), in DDL order. Exported so a
# test (and STATS-013, at its build time) can assert the canonical schema.
SHOW_REGISTRY_COLUMNS: Tuple[str, ...] = (
    "show_id", "name", "persona_id", "slot_day_of_week", "slot_hour",
    "format_type", "lineup_status", "pinned", "created_at", "last_aired_at",
    "paused_at", "lineup_fingerprint",
)


# ========================================================================== #
# Fingerprint helpers (REQ-SQ-001) — the comparable text the firewall scores.
# ========================================================================== #


def make_fingerprint(name: str, theme: str, music_angle: str) -> str:
    """Build the ``lineup_fingerprint`` JSON text for a concept (REQ-SH-001 column).

    Stores the three identity fields AND a flat ``text`` = ``name + theme +
    music_angle`` so the firewall compares a clean concatenated angle string (not raw
    JSON punctuation) with ``angle_similarity``. JSON keeps the row self-describing
    (and STATS-013-friendly) without forcing the metric to tokenize braces/quotes.
    """
    text = f"{name or ''} {theme or ''} {music_angle or ''}".strip()
    return json.dumps(
        {"name": name or "", "theme": theme or "",
         "music_angle": music_angle or "", "text": text},
        ensure_ascii=False,
    )


def fingerprint_text(fingerprint: Optional[str]) -> str:
    """Extract the comparable angle text from a stored ``lineup_fingerprint``.

    Tolerant: a JSON object uses its ``text`` field (or rebuilds from name/theme/
    music_angle); a non-JSON / legacy / empty value is returned as-is. Never raises —
    a malformed fingerprint degrades to a best-effort string (NFR-LU-2 isolation).
    """
    if not fingerprint:
        return ""
    try:
        obj = json.loads(fingerprint)
    except (ValueError, TypeError):
        return str(fingerprint)
    if not isinstance(obj, dict):
        return str(fingerprint)
    text = obj.get("text")
    if isinstance(text, str) and text.strip():
        return text
    parts = [obj.get("name", ""), obj.get("theme", ""), obj.get("music_angle", "")]
    return " ".join(str(p) for p in parts if p).strip()


# ========================================================================== #
# M1 — ShowRegistry: the durable recurring-slot identity store (events.db)
# ========================================================================== #


class ShowRegistry:
    """The canonical ``show_registry`` store in the ``events.db`` partition (REQ-SH-001).

    Mirrors ``analytics.PlayEventsStore`` / ``like.AffinityStore``: ONE shared
    connection + WAL write lock per ``events.db`` file via the DATASTORE-022
    ``sqlite_store._conn_for`` registry (REQ-DP-003) — it never opens a competing
    connection, and it never touches ``brain.db``/``knowledge.db``.

    Permanence (NFR-LU-6): there is deliberately NO delete/drop/purge/vacuum method.
    Rows (incl. ``hiatus``/``discontinued``/``retired``) persist forever as the
    recurring-lineup history + the cross-persona firewall corpus. Writes are
    single-file: the row is canonical; any OPS-004 ledger journal is a SEPARATE
    best-effort write (no cross-file atomic write).
    """

    def __init__(self, db_path: str) -> None:
        # Import here (not at module top) to mirror PlayEventsStore: the per-file
        # registry still guarantees one connection per file even mid-refactor.
        from . import sqlite_store

        self.handle = sqlite_store._conn_for(db_path)
        sqlite_store._ensure_meta(self.handle)
        with self.handle.lock:
            # CREATE-IF-NOT-EXISTS: an already-populated events.db (play_events/likes
            # rows) is untouched; re-initialization is idempotent (AC-SH-001 / D9).
            self.handle.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS show_registry (
                    show_id            TEXT PRIMARY KEY,
                    name               TEXT NOT NULL DEFAULT '',
                    persona_id         TEXT NOT NULL DEFAULT '',
                    slot_day_of_week   INTEGER NOT NULL DEFAULT 0,
                    slot_hour          INTEGER NOT NULL DEFAULT 0,
                    format_type        TEXT NOT NULL DEFAULT '',
                    lineup_status      TEXT NOT NULL DEFAULT 'concept',
                    pinned             INTEGER NOT NULL DEFAULT 0,
                    created_at         REAL NOT NULL DEFAULT 0,
                    last_aired_at      REAL,
                    paused_at          REAL,
                    lineup_fingerprint TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_sr_persona_day_status
                    ON show_registry(persona_id, slot_day_of_week, lineup_status);
                CREATE INDEX IF NOT EXISTS idx_sr_status
                    ON show_registry(lineup_status);
                """
            )
            self.handle.conn.commit()

    # -- writes (upsert; never delete) ------------------------------------- #

    def register(self, *, show_id: str, name: str, persona_id: str,
                 slot_day_of_week: int, slot_hour: int, format_type: str,
                 lineup_status: str, pinned: bool = False, fingerprint: str = "",
                 created_at: Optional[float] = None,
                 last_aired_at: Optional[float] = None,
                 paused_at: Optional[float] = None) -> None:
        """Insert or update one recurring-slot identity row (idempotent by ``show_id``).

        Uses ON CONFLICT DO UPDATE (upsert) — the same logical row is updated in place,
        never delete+reinsert, so permanence (NFR-LU-6) holds even on re-register.
        ``created_at`` is preserved on conflict (a row's birth time is immutable).
        """
        ts = float(created_at) if created_at is not None else time.time()
        with self.handle.lock:
            self.handle.conn.execute(
                """
                INSERT INTO show_registry(
                    show_id, name, persona_id, slot_day_of_week, slot_hour,
                    format_type, lineup_status, pinned, created_at,
                    last_aired_at, paused_at, lineup_fingerprint)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(show_id) DO UPDATE SET
                    name=excluded.name,
                    persona_id=excluded.persona_id,
                    slot_day_of_week=excluded.slot_day_of_week,
                    slot_hour=excluded.slot_hour,
                    format_type=excluded.format_type,
                    lineup_status=excluded.lineup_status,
                    pinned=excluded.pinned,
                    last_aired_at=excluded.last_aired_at,
                    paused_at=excluded.paused_at,
                    lineup_fingerprint=excluded.lineup_fingerprint
                """,
                (str(show_id), str(name or ""), str(persona_id or ""),
                 int(slot_day_of_week), int(slot_hour), str(format_type or ""),
                 str(lineup_status or LINEUP_CONCEPT), 1 if pinned else 0, ts,
                 (float(last_aired_at) if last_aired_at is not None else None),
                 (float(paused_at) if paused_at is not None else None),
                 str(fingerprint or "")),
            )
            self.handle.conn.commit()

    def set_status(self, show_id: str, lineup_status: str, *,
                   paused_at: Optional[float] = None) -> None:
        """Transition a row's ``lineup_status`` (and optionally stamp ``paused_at``).

        Pure status update — the row is never removed. ``paused_at`` is only written
        when supplied (an ``active->hiatus`` transition stamps it; others leave it).
        """
        with self.handle.lock:
            if paused_at is not None:
                self.handle.conn.execute(
                    "UPDATE show_registry SET lineup_status=?, paused_at=? WHERE show_id=?",
                    (str(lineup_status), float(paused_at), str(show_id)),
                )
            else:
                self.handle.conn.execute(
                    "UPDATE show_registry SET lineup_status=? WHERE show_id=?",
                    (str(lineup_status), str(show_id)),
                )
            self.handle.conn.commit()

    def set_last_aired(self, show_id: str, ts: float) -> None:
        """Stamp the most-recent airing time (does not change status; never deletes)."""
        with self.handle.lock:
            self.handle.conn.execute(
                "UPDATE show_registry SET last_aired_at=? WHERE show_id=?",
                (float(ts), str(show_id)),
            )
            self.handle.conn.commit()

    # -- reads ------------------------------------------------------------- #

    def get(self, show_id: str) -> Optional[Dict[str, Any]]:
        with self.handle.lock:
            cur = self.handle.conn.execute(
                "SELECT * FROM show_registry WHERE show_id=?", (str(show_id),)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def all_rows(self) -> List[Dict[str, Any]]:
        with self.handle.lock:
            cur = self.handle.conn.execute(
                "SELECT * FROM show_registry ORDER BY created_at ASC, show_id ASC"
            )
            return [dict(r) for r in cur.fetchall()]

    def count(self) -> int:
        with self.handle.lock:
            cur = self.handle.conn.execute("SELECT COUNT(*) AS n FROM show_registry")
            return int(cur.fetchone()["n"])

    def non_active_rows(self, *, exclude_pinned: bool = True,
                        exclude_show_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """The firewall scan corpus (REQ-SQ-001): every row whose ``lineup_status`` is
        NOT ``active``, optionally excluding ``pinned`` flagships and one show id.

        This is the cross-persona, cross-time memory the similarity firewall vets new
        concepts against. The ``lineup_status``/``pinned`` filters ride the
        ``idx_sr_status`` index; the scan stays OFF the playout pull path (NFR-LU-1).
        """
        sql = "SELECT * FROM show_registry WHERE lineup_status != ?"
        params: List[Any] = [LINEUP_ACTIVE]
        if exclude_pinned:
            sql += " AND pinned = 0"
        if exclude_show_id is not None:
            sql += " AND show_id != ?"
            params.append(str(exclude_show_id))
        with self.handle.lock:
            cur = self.handle.conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def rows_registered_after(self, ts: float, *, exclude_show_id: Optional[str] = None,
                              exclude_pinned: bool = True) -> List[Dict[str, Any]]:
        """Rows registered at/after ``ts`` — the "meanwhile-registered" corpus for the
        long-hiatus reactivation re-vet (REQ-SQ-003 / B9).

        Unlike ``non_active_rows`` this intentionally includes ACTIVE rows: reactivating
        a slept show into a near-duplicate of a show that went LIVE during the hiatus is
        exactly the hazard SQ-003 guards. Pinned rows and the reactivating show itself
        are excluded.
        """
        sql = "SELECT * FROM show_registry WHERE created_at >= ?"
        params: List[Any] = [float(ts)]
        if exclude_pinned:
            sql += " AND pinned = 0"
        if exclude_show_id is not None:
            sql += " AND show_id != ?"
            params.append(str(exclude_show_id))
        with self.handle.lock:
            cur = self.handle.conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


# ========================================================================== #
# M2 — the cross-persona similarity firewall (REQ-SQ-001/002/003)
# ========================================================================== #


@dataclass
class Concept:
    """A candidate recurring-show concept the firewall vets.

    ``text`` (``name + theme + music_angle``) is the string scored by
    ``angle_similarity`` (REQ-SQ-001). ``show`` optionally carries the underlying
    SHOWS-020 ``Show`` the consumed ``propose_show`` produced (so a caller can persist
    it after admission) — the firewall itself only reads ``text``.
    """

    name: str = ""
    theme: str = ""
    music_angle: str = ""
    show: Any = None

    @property
    def text(self) -> str:
        return f"{self.name or ''} {self.theme or ''} {self.music_angle or ''}".strip()


@dataclass
class FirewallResult:
    """The outcome of a firewall vet — a structured verdict the director consumes.

    ``status`` is one of:
      - ``admitted``  : ``concept`` cleared the firewall (score strictly < threshold);
      - ``escalated`` : the bounded regenerate was exhausted (impasse) — leave the slot
                        on its existing safe state, NEVER bind ``concept`` (it is None);
      - ``failed``    : concept generation faulted/returned None (NFR-LU-4) — slot stays
                        unscheduled, no crash;
      - ``reactivate``: (re-vet only) the show may reactivate (short hiatus / pinned /
                        cleared re-vet).
    """

    status: str
    concept: Optional[Concept] = None
    score: float = 0.0
    matched_show_id: Optional[str] = None
    attempts: int = 0
    detail: str = ""


class CrossPersonaFirewall:
    """The cross-persona, cross-time similarity firewall (Group SQ).

    REUSES the EXISTING ``shows.angle_similarity`` (token-set Jaccard, [0..1]) and the
    EXISTING ``shows_novelty_threshold`` (default 0.6) + ``shows_max_regenerate``
    (default 3) knobs — it defines NO second metric and forks no per-persona novelty
    engine (NFR-LU-5). All work here is bounded + exception-isolated, OFF the playout
    pull path (NFR-LU-1/2).
    """

    def __init__(self, registry: ShowRegistry, cfg: Any = None, *,
                 threshold: Optional[float] = None,
                 max_regen: Optional[int] = None) -> None:
        self.registry = registry
        if threshold is not None:
            self.threshold = float(threshold)
        else:
            self.threshold = float(getattr(cfg, "shows_novelty_threshold", 0.6))
        if max_regen is not None:
            self.max_regen = int(max_regen)
        else:
            self.max_regen = int(getattr(cfg, "shows_max_regenerate", 3))

    # -- scoring (REQ-SQ-001) ---------------------------------------------- #

    @staticmethod
    def _score_against(concept_text: str,
                       corpus: List[Tuple[str, str]]) -> Tuple[float, Optional[str]]:
        """Max ``angle_similarity`` of ``concept_text`` over ``corpus`` (id, fp-text).

        Returns (best_score, matching_show_id). An empty corpus scores 0.0 (nothing to
        collide with) — the first concept passes.
        """
        best = 0.0
        matched: Optional[str] = None
        for show_id, text in corpus:
            s = angle_similarity(concept_text, text)
            if s > best:
                best, matched = s, show_id
        return best, matched

    def score_concept(self, concept_text: str, *,
                      exclude_show_id: Optional[str] = None) -> Tuple[float, Optional[str]]:
        """Score a concept against EVERY non-active, non-pinned row across all personas
        (REQ-SQ-001). Returns (max_score, matched_show_id)."""
        corpus = [
            (r["show_id"], fingerprint_text(r["lineup_fingerprint"]))
            for r in self.registry.non_active_rows(
                exclude_pinned=True, exclude_show_id=exclude_show_id)
        ]
        return self._score_against(concept_text, corpus)

    def is_novel(self, concept_text: str, *,
                 exclude_show_id: Optional[str] = None) -> bool:
        """True when the concept scores strictly BELOW the threshold against every
        non-active cross-persona row (REQ-SQ-002 pass condition)."""
        return self.score_concept(
            concept_text, exclude_show_id=exclude_show_id)[0] < self.threshold

    # -- admit + bounded regenerate + escalate (REQ-SQ-002) ---------------- #

    def admit(self, generate: Callable[[], Optional[Concept]], *,
              exclude_show_id: Optional[str] = None) -> FirewallResult:
        """Vet a generated concept; on a collision, regenerate (bounded), else escalate.

        ``generate`` is the concept source — typically a closure over the consumed
        ``ShowEngine.propose_show``. The loop runs ``max_regen + 1`` times (mirroring
        ``propose_show``'s own ``attempts <= max_regen`` bound): 1 initial concept + up
        to ``max_regen`` regenerations. The FIRST concept scoring strictly < threshold
        is admitted. If the bound is exhausted with no clean concept, the firewall
        ESCALATES (never loops, never binds a near-duplicate).

        Exception-isolated (NFR-LU-4): a ``generate`` fault or a ``None`` return (e.g. a
        ``propose_show`` LLM/charter failure) yields a ``failed`` verdict — the slot
        stays unscheduled and the tick survives.
        """
        attempts = 0
        last_score = 0.0
        last_match: Optional[str] = None
        while attempts <= self.max_regen:
            try:
                concept = generate()
            except Exception as exc:  # noqa: BLE001 - concept-gen is best-effort (NFR-LU-4)
                log_event(log, "lineup.firewall_generate_error", error=str(exc),
                          attempt=attempts)
                return FirewallResult(status="failed", attempts=attempts,
                                      detail=f"generate raised: {exc}")
            if concept is None:
                log_event(log, "lineup.firewall_generate_none", attempt=attempts)
                return FirewallResult(status="failed", attempts=attempts,
                                      detail="generate returned None")
            score, matched = self.score_concept(
                concept.text, exclude_show_id=exclude_show_id)
            if score < self.threshold:
                return FirewallResult(status="admitted", concept=concept, score=score,
                                      matched_show_id=matched, attempts=attempts + 1)
            last_score, last_match = score, matched
            log_event(log, "lineup.firewall_reject", attempt=attempts + 1,
                      score=round(score, 3), matched=matched)
            attempts += 1

        # Bounded retries exhausted -> escalate (REQ-SQ-002): never bind, never loop.
        log_event(log, "lineup.firewall_escalate", attempts=attempts,
                  score=round(last_score, 3), matched=last_match)
        return FirewallResult(status="escalated", score=last_score,
                              matched_show_id=last_match, attempts=attempts)

    # -- long-hiatus reactivation re-vet entry point (REQ-SQ-003) ---------- #

    def revet_reactivation(self, show_id: str, *, hiatus_age: float,
                           long_hiatus_bound: float,
                           generate: Optional[Callable[[], Optional[Concept]]] = None
                           ) -> FirewallResult:
        """The clean entry point the M4 hiatus state machine calls on reactivation.

        Behavior (REQ-SQ-003 / B9):
          - ``pinned`` flagship -> exempt, ``reactivate`` (no scan);
          - hiatus WITHIN the ``long_hiatus_bound`` -> ``reactivate`` (no re-vet);
          - a LONGER hiatus -> re-run the firewall against shows registered MEANWHILE
            (``created_at`` >= the show's ``paused_at``, excluding self + pinned). A
            score < threshold -> ``reactivate``. An over-threshold collision is treated
            like a rejected concept: regenerate via ``generate`` if supplied (the M4
            caller passes a ``propose_show`` closure), else ``escalated`` — never a
            silent reactivation into a near-duplicate.

        Exception-isolated: an unknown show id returns a ``failed`` verdict.
        """
        row = self.registry.get(show_id)
        if row is None:
            return FirewallResult(status="failed", detail="unknown show id")
        if bool(row.get("pinned")):
            return FirewallResult(status="reactivate", detail="pinned exempt")
        if hiatus_age <= long_hiatus_bound:
            return FirewallResult(status="reactivate", detail="short hiatus")

        paused_at = row.get("paused_at") or row.get("created_at") or 0.0
        corpus = [
            (r["show_id"], fingerprint_text(r["lineup_fingerprint"]))
            for r in self.registry.rows_registered_after(
                float(paused_at), exclude_show_id=show_id, exclude_pinned=True)
        ]
        own_text = fingerprint_text(row.get("lineup_fingerprint"))
        score, matched = self._score_against(own_text, corpus)
        if score < self.threshold:
            return FirewallResult(status="reactivate", score=score,
                                  detail="re-vet clear")
        if generate is not None:
            return self.admit(generate, exclude_show_id=show_id)
        return FirewallResult(status="escalated", score=score, matched_show_id=matched,
                              detail="long-hiatus collision")
