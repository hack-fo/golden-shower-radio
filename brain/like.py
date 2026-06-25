"""SPEC-RADIO-LIKE-015 — listener heart/like + implicit drop-off + soft affinity.

This module is the listener-affinity engine. It turns two listener signals into a SINGLE,
SOFT, time-decayed affinity weight the director MAY weigh and MAY ignore:

  Group LH — the EXPLICIT heart/like. The only explicit affinity input — there is no dislike
    button (REQ-LH-001). A like is authenticated by a signed HMAC token bound to the
    currently-airing track + an issue time + a nonce (REQ-LH-002 / REQ-LA-001), so the brain
    knows the like is for a real on-air track, not a replay or a forgery. A like is identity-
    deduped (same hashed cookie can't like the same recording twice in the window) and rate-
    limited (a per-identity cap per track per window) (REQ-LH-003 / REQ-LA-003).

  Group LD — the IMPLICIT drop-off. A NEGATIVE signal derived from listeners disconnecting
    within a short window after a track starts (REQ-LD-001). It is NOT a button. The brain
    polls Icecast's public ``/status-json.xsl`` for AGGREGATE listener counts per mount
    (REQ-LD-002), in a bounded background thread that NEVER blocks playout (REQ-LD-004). Below
    a minimum-audience floor the measure is suppressed (noise + privacy); a disconnect fraction
    at/above the configured threshold within the drop-off window is the drop-off signal
    (REQ-LD-003).

  Group LS — both signals normalize into a soft affinity entry keyed on the canonical ENRICH-012
    recording key (``Track.key`` / ``normalize_key``) and stored in SQLite (REQ-LS-001 /
    REQ-LH-004). [HARD] Affinity is a SOFT weight ONLY — NEVER hard rotation control: no
    force-play, force-skip, force-rotate (REQ-LS-002). Counts are noisy, identity-deduped,
    time-decayed weak priors — never a satisfaction target (REQ-LS-003). Each signal carries a
    timestamp; stale signals beyond a configurable age are ignored/purged (REQ-LS-004).

  Group LP — PRIVACY. The like identity is ``SHA256(cookie_value + salt)`` — no raw cookie,
    no account, no raw PII (REQ-LP-001/003). Drop-off is aggregate-only — a total listener
    count delta, no individual tracking (REQ-LP-002).

  Group LX — OBSERVABILITY. No public leaderboard; a like response only confirms per-listener
    receipt (REQ-LX-001/002). Every like / invalid-token / rate-limit / drop-off is logged
    (REQ-LX-003).

[HARD] never block playout: every public method is exception-isolated — it logs and returns a
safe default; the Icecast poll runs in a bounded daemon thread. The whole subsystem is OFF by
default (``like_enabled`` False) — with it off the endpoints 404 and the poll never starts, so
the station behaves exactly as before this SPEC.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .logging_setup import log_event

log = logging.getLogger("brain.like")


# --------------------------------------------------------------------------- #
# Privacy helper (Group LP)
# --------------------------------------------------------------------------- #


def hash_identity(cookie_value: str, salt: str) -> str:
    """REQ-LP-001: the like identity = ``SHA256(cookie_value + salt)``.

    NEVER store the raw cookie — only this one-way hash. An empty cookie still hashes (to a
    stable salted digest of ""), so an identity is always derivable; the caller decides whether
    a missing cookie is acceptable. The salt is ``BRAIN_LIKE_COOKIE_SALT`` (a secret).
    """
    h = hashlib.sha256()
    h.update((salt or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((cookie_value or "").encode("utf-8"))
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Group LA / LH — the signed like token
# --------------------------------------------------------------------------- #


@dataclass
class TokenVerdict:
    """The outcome of verifying a like token (Group LA)."""
    valid: bool
    track_key: str = ""
    cause: str = ""  # "" on success; else expired | bad_signature | malformed | no_secret


class LikeTokener:
    """Mint + verify the HMAC like-token (REQ-LA-001 / REQ-LH-002).

    Token = ``HMAC-SHA256(track_key + "|" + airing_started_at + "|" + nonce, secret)``, carried
    to the client as ``"{track_key}.{issued_at}.{nonce}.{hexmac}"``. Verification recomputes the
    MAC over the SAME three bound fields and compares in constant time, then enforces the TTL
    (default 300s, ``BRAIN_LIKE_TOKEN_TTL``). With no secret configured every token is invalid
    (the feature fails closed), which is why the endpoints additionally gate on ``like_enabled``.

    The token binds the like to a SPECIFIC on-air track + issue time + nonce, so it cannot be
    replayed for a different track or re-used past its TTL (REQ-LA-003 anti-flood, with the cap +
    dedup enforced separately by ``LikeGate``).
    """

    def __init__(self, secret: str, ttl_seconds: int = 300) -> None:
        self._secret = (secret or "").encode("utf-8")
        self._ttl = max(1, int(ttl_seconds))

    def _mac(self, track_key: str, issued_at: int, nonce: str) -> str:
        msg = f"{track_key}|{issued_at}|{nonce}".encode("utf-8")
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def mint(self, track_key: str, *, issued_at: Optional[int] = None,
             nonce: Optional[str] = None) -> Dict[str, Any]:
        """Mint a token for ``track_key`` (REQ-LA-001). Returns
        ``{"token": str, "expires_at": int, "issued_at": int}``. Exception-isolated: on any
        failure (e.g. no secret) it returns an empty token + expiry 0, never raises."""
        try:
            ts = int(issued_at if issued_at is not None else time.time())
            nz = nonce if nonce is not None else os.urandom(8).hex()
            mac = self._mac(track_key, ts, nz)
            token = f"{track_key}.{ts}.{nz}.{mac}"
            return {"token": token, "issued_at": ts, "expires_at": ts + self._ttl}
        except Exception as exc:  # noqa: BLE001 - minting never raises into the request path
            log_event(log, "like.token_mint_error", error=str(exc))
            return {"token": "", "issued_at": 0, "expires_at": 0}

    def verify(self, token: str, *, now: Optional[int] = None) -> TokenVerdict:
        """Verify a token (REQ-LA-002). Returns a :class:`TokenVerdict`. Never raises.

        Order: structural parse -> constant-time MAC compare (forgery) -> TTL (expiry). The
        bound ``track_key`` is recovered from the token itself and re-validated by the MAC, so a
        tampered track_key fails the signature check.
        """
        try:
            if not self._secret:
                return TokenVerdict(valid=False, cause="no_secret")
            parts = (token or "").split(".")
            if len(parts) != 4:
                return TokenVerdict(valid=False, cause="malformed")
            track_key, ts_str, nonce, mac = parts
            try:
                issued_at = int(ts_str)
            except (TypeError, ValueError):
                return TokenVerdict(valid=False, cause="malformed")
            expected = self._mac(track_key, issued_at, nonce)
            if not hmac.compare_digest(expected, mac):
                return TokenVerdict(valid=False, cause="bad_signature")
            cur = int(now if now is not None else time.time())
            if cur - issued_at > self._ttl or cur < issued_at - 5:
                return TokenVerdict(valid=False, track_key=track_key, cause="expired")
            return TokenVerdict(valid=True, track_key=track_key)
        except Exception as exc:  # noqa: BLE001 - verification never raises into the request path
            log_event(log, "like.token_verify_error", error=str(exc))
            return TokenVerdict(valid=False, cause="malformed")


# --------------------------------------------------------------------------- #
# Group LS — the soft affinity store (SQLite, events.db)
# --------------------------------------------------------------------------- #


class AffinityStore:
    """Soft affinity persistence (REQ-LS-001) — two tables in ``events.db``.

      ``affinity_signals`` — one append row per normalized soft signal (a like or a drop-off),
        keyed on the canonical recording key (REQ-LH-004 / REQ-LS-001). ``weight`` is +ve for a
        like, -ve for a drop-off; ``created_at`` is the timestamp the decay/purge reads
        (REQ-LS-004). This is data only — never a rotation control (REQ-LS-002).

      ``like_identities`` — per-(identity, track_key) dedup + rate-limit ledger (REQ-LH-003 /
        REQ-LA-003). One row per like accepted from a hashed identity for a recording, carrying
        ``created_at`` for the dedup window + the per-identity cap-per-window count. NO raw cookie
        is ever stored — only the SHA256 identity hash (REQ-LP-001).

    Lives in ``events.db`` (the append-heavy analytics file that already holds ``likes`` /
    ``play_events``) and SHARES that file's one connection + WAL write lock via the DATASTORE-022
    ``_conn_for`` registry, so it never opens a competing connection. Every method is exception-
    isolated by the caller (``LikeGate``); the raw store methods raise only on genuine DB faults.
    """

    def __init__(self, db_path: str) -> None:
        # Import here so the module imports cleanly even if sqlite_store is mid-refactor; the
        # shared per-file connection registry guarantees one connection per events.db file.
        from . import sqlite_store

        self.handle = sqlite_store._conn_for(db_path)
        sqlite_store._ensure_meta(self.handle)
        with self.handle.lock:
            self.handle.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS affinity_signals (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_key  TEXT NOT NULL,
                    kind       TEXT NOT NULL,
                    weight     REAL NOT NULL,
                    created_at REAL NOT NULL,
                    data       TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_affinity_track ON affinity_signals(track_key);
                CREATE INDEX IF NOT EXISTS idx_affinity_created ON affinity_signals(created_at);
                CREATE TABLE IF NOT EXISTS like_identities (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity   TEXT NOT NULL,
                    track_key  TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_like_id_pair
                    ON like_identities(identity, track_key, created_at);
                """
            )
            self.handle.conn.commit()

    # -- affinity_signals ---------------------------------------------------- #

    def record_signal(self, track_key: str, kind: str, weight: float,
                      *, created_at: Optional[float] = None,
                      data: Optional[Dict[str, Any]] = None) -> int:
        """Append one soft affinity signal. Returns the new row id. ``kind`` is
        ``"like"`` (+ve weight) or ``"drop_off"`` (-ve weight)."""
        ts = float(created_at if created_at is not None else time.time())
        blob = json.dumps(data, ensure_ascii=False) if data is not None else None
        with self.handle.lock:
            cur = self.handle.conn.execute(
                "INSERT INTO affinity_signals(track_key, kind, weight, created_at, data) "
                "VALUES(?,?,?,?,?)",
                (track_key, kind, float(weight), ts, blob),
            )
            self.handle.conn.commit()
            return int(cur.lastrowid or 0)

    def affinity_for(self, track_key: str, *, decay_seconds: float,
                     now: Optional[float] = None) -> float:
        """REQ-LS-004: the SOFT, time-decayed affinity weight for a recording.

        Sums the weights of every NON-STALE signal for the key — a signal older than
        ``decay_seconds`` is ignored. ``decay_seconds <= 0`` means no decay (all signals count).
        This is a weak prior the director MAY consult; it NEVER drives rotation (REQ-LS-002).
        """
        cur_ts = float(now if now is not None else time.time())
        with self.handle.lock:
            c = self.handle.conn.cursor()
            if decay_seconds and decay_seconds > 0:
                cutoff = cur_ts - float(decay_seconds)
                c.execute(
                    "SELECT COALESCE(SUM(weight), 0) AS w FROM affinity_signals "
                    "WHERE track_key=? AND created_at >= ?",
                    (track_key, cutoff),
                )
            else:
                c.execute(
                    "SELECT COALESCE(SUM(weight), 0) AS w FROM affinity_signals "
                    "WHERE track_key=?",
                    (track_key,),
                )
            return float(c.fetchone()["w"] or 0.0)

    def purge_stale(self, *, decay_seconds: float, now: Optional[float] = None) -> int:
        """REQ-LS-004: delete signals older than ``decay_seconds``. Returns rows removed.
        ``decay_seconds <= 0`` is a no-op (no decay configured)."""
        if not decay_seconds or decay_seconds <= 0:
            return 0
        cutoff = float(now if now is not None else time.time()) - float(decay_seconds)
        with self.handle.lock:
            cur = self.handle.conn.execute(
                "DELETE FROM affinity_signals WHERE created_at < ?", (cutoff,)
            )
            self.handle.conn.commit()
            return int(cur.rowcount or 0)

    def signal_count(self) -> int:
        with self.handle.lock:
            c = self.handle.conn.cursor()
            c.execute("SELECT COUNT(*) AS n FROM affinity_signals")
            return int(c.fetchone()["n"])

    # -- like_identities (dedup + rate-limit) -------------------------------- #

    def identity_likes_in_window(self, identity: str, track_key: str,
                                 window_seconds: float,
                                 *, now: Optional[float] = None) -> int:
        """Count this identity's likes for ``track_key`` within the trailing window
        (REQ-LH-003 dedup / REQ-LA-003 per-identity cap)."""
        cutoff = float(now if now is not None else time.time()) - float(window_seconds)
        with self.handle.lock:
            c = self.handle.conn.cursor()
            c.execute(
                "SELECT COUNT(*) AS n FROM like_identities "
                "WHERE identity=? AND track_key=? AND created_at >= ?",
                (identity, track_key, cutoff),
            )
            return int(c.fetchone()["n"])

    def record_identity_like(self, identity: str, track_key: str,
                             *, created_at: Optional[float] = None) -> None:
        """Record one accepted like for the (identity, track_key) dedup/rate ledger."""
        ts = float(created_at if created_at is not None else time.time())
        with self.handle.lock:
            self.handle.conn.execute(
                "INSERT INTO like_identities(identity, track_key, created_at) VALUES(?,?,?)",
                (identity, track_key, ts),
            )
            self.handle.conn.commit()


# --------------------------------------------------------------------------- #
# Group LH / LA — the like gate (validate + dedup + rate-limit + record)
# --------------------------------------------------------------------------- #


@dataclass
class LikeResult:
    """The verdict for a POST /api/like (Group LX surface)."""
    received: bool
    cause: str = ""  # "" on accept; else token cause | rate_limited | duplicate | no_identity


class LikeGate:
    """Validate a like, enforce dedup + rate-limit, and record the soft signal (Group LH/LA).

    The single chokepoint POST /api/like routes through. Steps (each a hard gate, REQ-LA-002):
      1. verify the HMAC token -> reject expired/forged (REQ-LA-001/003)
      2. derive the hashed identity from the cookie + salt (REQ-LP-001)
      3. dedup: the same identity can't like the same recording twice within the dedup window
         (REQ-LH-003)
      4. rate-limit: at most ``cap`` likes per identity per recording per window (REQ-LA-003)
      5. record a +ve soft affinity signal on the canonical recording key (REQ-LS-001/LH-004)

    Exception-isolated (REQ-LX / never-block): any internal fault logs and returns
    ``LikeResult(received=False, cause="error")`` rather than raising into the request thread.
    """

    LIKE_WEIGHT = 1.0

    def __init__(self, tokener: LikeTokener, store: AffinityStore, *,
                 cookie_salt: str, dedup_window_hours: float, per_identity_cap: int) -> None:
        self.tokener = tokener
        self.store = store
        self._salt = cookie_salt or ""
        self._dedup_window_seconds = max(0.0, float(dedup_window_hours) * 3600.0)
        self._cap = max(1, int(per_identity_cap))

    def record_like(self, token: str, cookie_value: str,
                    *, now: Optional[float] = None) -> LikeResult:
        """The POST /api/like path. Returns a :class:`LikeResult`. Never raises."""
        try:
            cur = float(now if now is not None else time.time())
            verdict = self.tokener.verify(token, now=int(cur))
            if not verdict.valid:
                log_event(log, "like.token_invalid", cause=verdict.cause)
                return LikeResult(received=False, cause=verdict.cause or "invalid_token")
            track_key = verdict.track_key
            if not track_key:
                return LikeResult(received=False, cause="malformed")
            if not (cookie_value or "").strip():
                # No identity cookie -> we cannot dedup/rate-limit, so we refuse (anti-flood).
                log_event(log, "like.no_identity", track_key=track_key)
                return LikeResult(received=False, cause="no_identity")
            identity = hash_identity(cookie_value, self._salt)
            prior = self.store.identity_likes_in_window(
                identity, track_key, self._dedup_window_seconds, now=cur)
            if prior >= 1 and self._dedup_window_seconds > 0:
                # Same identity already liked this recording inside the dedup window.
                if prior >= self._cap:
                    log_event(log, "like.rate_limited", track_key=track_key, count=prior)
                    return LikeResult(received=False, cause="rate_limited")
                log_event(log, "like.duplicate", track_key=track_key, count=prior)
                return LikeResult(received=False, cause="duplicate")
            self.store.record_identity_like(identity, track_key, created_at=cur)
            self.store.record_signal(
                track_key, "like", self.LIKE_WEIGHT, created_at=cur,
                data={"source": "heart"})
            log_event(log, "like.received", track_key=track_key)
            return LikeResult(received=True)
        except Exception as exc:  # noqa: BLE001 - never let a like crash the request thread
            log_event(log, "like.record_error", error=str(exc))
            return LikeResult(received=False, cause="error")


# --------------------------------------------------------------------------- #
# Group LD — the implicit drop-off engine (bounded Icecast poll)
# --------------------------------------------------------------------------- #


@dataclass
class _MountSample:
    """One station-wide listener-count sample at a moment (aggregate only — REQ-LP-002)."""
    at: float
    listeners: int


class DropOffEngine:
    """Derive a NEGATIVE drop-off signal from aggregate listener disconnects (Group LD).

    A bounded background daemon thread polls Icecast's public ``/status-json.xsl`` (REQ-LD-002)
    and aggregates the per-mount listener counts to ONE station-wide number (D-L-4) — never an
    individual is tracked (REQ-LP-002). When a track starts on air (``note_track_start``), the
    engine snapshots the audience; after the drop-off window (default 45s) it compares: if the
    audience was at/above the minimum floor (default 3) and the fraction lost is at/above the
    threshold (default 0.50), it records a -ve soft affinity signal for that track's canonical
    key (REQ-LD-001/003 / REQ-LS-001).

    [HARD] NEVER blocks playout (REQ-LD-004): the poll runs in its own daemon thread with an
    explicit per-request timeout, bounded retries, and full exception isolation. With
    ``like_enabled`` False the engine never starts; ``note_track_start`` is then a no-op.
    """

    def __init__(self, cfg: Any, store: AffinityStore, stop_event: threading.Event,
                 *, fetch: Optional[Callable[[], List[Tuple[str, int]]]] = None) -> None:
        self._enabled: bool = bool(getattr(cfg, "like_enabled", False))
        self._store = store
        self._stop = stop_event
        self._window: float = float(getattr(cfg, "like_drop_off_window", 45))
        self._min_audience: int = int(getattr(cfg, "like_min_audience", 3))
        self._fraction: float = float(getattr(cfg, "like_drop_off_fraction", 0.5))
        self._poll_interval: float = max(2.0, self._window / 3.0)
        self._http_timeout: float = float(getattr(cfg, "like_drop_off_window", 45)) / 3.0 or 5.0
        self._http_timeout = min(10.0, max(2.0, self._http_timeout))
        self._max_retries: int = 2
        self._url: str = self._status_url(cfg)
        # Injectable fetch (tests pass a fake) -> [(mount, listeners), ...]. Default = Icecast.
        self._fetch = fetch or self._fetch_icecast
        self._lock = threading.Lock()
        self._latest = 0  # most-recent aggregate listener count
        # track_key -> (started_at, audience_at_start) awaiting a drop-off evaluation.
        self._pending: Dict[str, _MountSample] = {}
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _status_url(cfg: Any) -> str:
        """The Icecast status JSON URL (D-L-2). Prefers an explicit ``icecast_url``; otherwise
        derives from the public host/port. Admin stats are used when admin creds are set."""
        explicit = (getattr(cfg, "icecast_url", "") or "").strip()
        base = explicit.rstrip("/") if explicit else f"http://icecast:{int(getattr(cfg, 'icecast_public_port', 8000))}"
        admin_user = (getattr(cfg, "icecast_admin_user", "") or "").strip()
        admin_pass = (getattr(cfg, "icecast_admin_pass", "") or "").strip()
        if admin_user and admin_pass:
            return f"{base}/admin/stats"
        return f"{base}/status-json.xsl"

    # -- lifecycle ----------------------------------------------------------- #

    def start(self) -> None:
        """Launch the bounded poll thread. No-op when ``like_enabled`` is False (REQ-LD-004)."""
        if not self._enabled:
            return
        self._thread = threading.Thread(target=self._poll_loop, name="drop-off-poll", daemon=True)
        self._thread.start()
        log_event(log, "like.dropoff_started", url=self._url, window=self._window,
                  min_audience=self._min_audience, fraction=self._fraction)

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_once()
                self._evaluate_pending()
            except Exception as exc:  # noqa: BLE001 - the poll never crashes the daemon
                log_event(log, "like.dropoff_poll_error", error=str(exc))
            self._stop.wait(self._poll_interval)

    def _poll_once(self) -> None:
        """One bounded poll: fetch aggregate listeners, update the latest count."""
        total = self._aggregate_listeners()
        if total is None:
            return
        with self._lock:
            self._latest = total

    def _aggregate_listeners(self) -> Optional[int]:
        """REQ-LD-002 / D-L-4: per-mount counts summed to ONE station-wide number. Bounded
        retries; returns None on persistent failure (never raises)."""
        for attempt in range(self._max_retries + 1):
            try:
                mounts = self._fetch()
                if mounts is None:
                    continue
                return sum(max(0, int(n)) for _, n in mounts)
            except Exception as exc:  # noqa: BLE001
                if attempt >= self._max_retries:
                    log_event(log, "like.dropoff_fetch_error", error=str(exc))
                    return None
        return None

    def _fetch_icecast(self) -> List[Tuple[str, int]]:
        """Fetch + parse Icecast ``status-json.xsl`` -> [(mount, listeners)]. Bounded timeout."""
        req = urllib.request.Request(self._url)
        req.add_header("User-Agent", "GoldenShowerRadio/1.0 (drop-off poll)")
        with urllib.request.urlopen(req, timeout=self._http_timeout) as resp:
            body = resp.read()
        data = json.loads(body.decode("utf-8", "replace"))
        return self._parse_status_json(data)

    @staticmethod
    def _parse_status_json(data: Any) -> List[Tuple[str, int]]:
        """Parse Icecast status JSON into [(mount, listeners)]. Tolerant of the single-source
        (dict) and multi-source (list) shapes; an unparseable entry contributes 0."""
        out: List[Tuple[str, int]] = []
        try:
            icestats = data.get("icestats", {}) if isinstance(data, dict) else {}
            source = icestats.get("source")
            if source is None:
                return out
            sources = source if isinstance(source, list) else [source]
            for s in sources:
                if not isinstance(s, dict):
                    continue
                mount = str(s.get("listenurl", "") or s.get("server_name", "") or "?")
                try:
                    listeners = int(s.get("listeners", 0) or 0)
                except (TypeError, ValueError):
                    listeners = 0
                out.append((mount, listeners))
        except Exception:  # noqa: BLE001 - a malformed status doc yields no samples, never raises
            return []
        return out

    # -- track lifecycle hooks ----------------------------------------------- #

    def note_track_start(self, track_key: str, *, now: Optional[float] = None) -> None:
        """Snapshot the audience when ``track_key`` starts on air (REQ-LD-001). No-op when
        disabled. Exception-isolated — never raises into the airing path."""
        if not self._enabled or not track_key:
            return
        try:
            cur = float(now if now is not None else time.time())
            with self._lock:
                self._pending[track_key] = _MountSample(at=cur, listeners=self._latest)
        except Exception as exc:  # noqa: BLE001
            log_event(log, "like.dropoff_note_error", error=str(exc))

    def _evaluate_pending(self, *, now: Optional[float] = None) -> None:
        """Evaluate any track whose drop-off window has elapsed (REQ-LD-003)."""
        cur = float(now if now is not None else time.time())
        with self._lock:
            latest = self._latest
            due = [(k, s) for k, s in self._pending.items() if cur - s.at >= self._window]
            for k, _ in due:
                self._pending.pop(k, None)
        for track_key, sample in due:
            self._maybe_record_dropoff(track_key, sample, latest, cur)

    def _maybe_record_dropoff(self, track_key: str, sample: _MountSample,
                              latest: int, now: float) -> None:
        """Apply the floor + fraction test and record a -ve signal on drop-off (REQ-LD-003)."""
        try:
            start_audience = sample.listeners
            if start_audience < self._min_audience:
                # Below the minimum-audience floor — suppress (noise + privacy, REQ-LD-003).
                return
            lost = max(0, start_audience - latest)
            fraction = lost / start_audience if start_audience > 0 else 0.0
            if fraction >= self._fraction:
                self._store.record_signal(
                    track_key, "drop_off", -1.0, created_at=now,
                    data={"start_audience": start_audience, "end_audience": latest,
                          "fraction": round(fraction, 3)})
                log_event(log, "like.dropoff_detected", track_key=track_key,
                          start_audience=start_audience, end_audience=latest,
                          fraction=round(fraction, 3))
        except Exception as exc:  # noqa: BLE001
            log_event(log, "like.dropoff_eval_error", error=str(exc))
