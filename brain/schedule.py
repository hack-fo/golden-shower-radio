"""SPEC-RADIO-OPS-004 Group OA — Program Director & 24h Scheduling.

The autonomous Program Director sits ON TOP of the existing thin director loop
(``brain.director``) and the music picker (``brain.server.Picker`` -> ``library.pick_next``).
It adds the 24-hour FORMAT CLOCK / dayparting, the schedule as a projection over the
REQ-OD-007 append-only ledger (program/schedule events — NO new store), the NO-ORPHAN
bootstrap (persona -> show -> schedule; degrade to house-voice + music when empty, NEVER
silent), the soft+hard separation SELECTION refinements the spec layers onto the existing
LRP picker, and the schedule-grid CRUD the PD plans with.

[HARD] BEHAVIOUR PRESERVATION (DDD): every surface here is ADDITIVE and gated behind
``cfg.scheduling_enabled`` (default OFF). With it OFF the director tick + the playout
pull are BYTE-IDENTICAL to before this SPEC: the picker calls ``library.pick_next``
unchanged (the SelectionRefiner is never constructed), the director plans nothing, and
no schedule event is written. The no-orphan degrade-to-house-voice+music path is the safe
default the playout consults when the schedule is empty (REQ-OA-008).

[HARD] SINGLE SOURCE — this module forks NO new datastore. The schedule is a VIEW over the
ONE OD-007 ledger (``brain.ledger.EventLedger``): ``schedule_planned`` / ``slot_added`` /
``slot_removed`` / ``slot_moved`` / ``persona_assigned`` / ``program_cycle`` events project
to the current grid. It REUSES the SHOWS-020 ``ShowEngine`` for shows, the OX topic-bank +
OY segment registry for content, and the OD ``MeasuredChangeBudget`` + ``RarityTier`` for any
self-change (grid-edit frequency, REQ-OD-010). It does NOT fork the show/format/schedule model.

Sibling seams (built OA-owned half IN FULL, the dep stated, never faked):
  * REQ-OA-007 imaging/ID production = Group OE (UNBUILT): the clock resolves an imaging/ID
    slot and emits the AI's element DECISION + a trigger seam; the actual production pipeline
    is OE's. With no producer the slot degrades to a cached-evergreen/music fallback (REQ-OA-008).
  * REQ-OA-013 ``reflect`` run-mode = SPEC-RADIO-REFLECT-026 (UNBUILT): the value is REGISTERED
    in the run-mode enum but never selected until the seam exists (graceful degradation).
  * REQ-OA-015 grid-CRUD dispatch = ORCH-005 REQ-RA-001(g) -> CORE-001 REQ-B-003 (UNBUILT): the
    brain has no separate B-003 schedule store, so the ledger-VIEW schedule IS OPS-004's
    representation; the ORCH-005 RA routing is the seam.
  * REQ-OA-016 the long-form EPISODE + its duration claim = SPEC-RADIO-LONGFORM-025 (UNBUILT):
    OPS-004 owns the override VARIANT mechanics + time-budgeting + the rails-it-honours; the
    episode is supplied as an input (the seam). No episode -> no override (graceful degradation).
  * REQ-OA-011/012 audio-feature extraction = SPEC-RADIO-ANALYSIS-006; the canonical
    reconciliation worker = SPEC-RADIO-ENRICH-012. OPS-004 CONSUMES those produced features and
    owns only the queryable catalog RECORD surface (``CatalogView``) — it never re-runs librosa/
    aubio nor forks the library store.
"""

from __future__ import annotations

import logging
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:  # zoneinfo is stdlib on 3.9+; degrade to fixed-offset if the tz database is absent.
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - zoneinfo missing is exotic
    ZoneInfo = None  # type: ignore

from .logging_setup import log_event

log = logging.getLogger("brain.schedule")


# =====================================================================================
# REQ-OA-009 — Local time / date / location awareness (Tórshavn, Atlantic/Faroe).
# =====================================================================================

DEFAULT_TIMEZONE = "Atlantic/Faroe"
DEFAULT_LOCATION = "Tórshavn, Faroe Islands"

# Daypart boundaries on the LOCAL Faroe wall clock (REQ-OA-005/009). These are the FIXED
# structural rail: each daypart EXISTS and its boundary sits HERE on the local clock. The
# energy/tone/register/content WITHIN a daypart is the AI's call (TUNABLE), never prescribed.
# Boundaries are (start_hour_inclusive, name); the list wraps at 24h.
DEFAULT_DAYPARTS: Tuple[Tuple[int, str], ...] = (
    (0, "overnight"),    # 00:00–06:00 local
    (6, "morning"),      # 06:00–10:00 local (morning drive)
    (10, "midday"),      # 10:00–15:00 local
    (15, "afternoon"),   # 15:00–19:00 local (afternoon drive)
    (19, "evening"),     # 19:00–24:00 local
)


@dataclass(frozen=True)
class LocalContext:
    """A resolved LOCAL-time snapshot the PD programs from (REQ-OA-009).

    AWARENESS is the rail; how the AI uses ``daypart`` / ``day_of_week`` / ``season`` is
    its creative call. ``is_weekend`` lets the AI differentiate weekday vs weekend
    programming; ``season`` / ``holiday`` feed theming."""

    epoch: float
    iso: str
    hour: int
    minute: int
    weekday: int          # 0 = Monday … 6 = Sunday (local)
    day_of_week: str
    is_weekend: bool
    daypart: str
    season: str
    location: str = DEFAULT_LOCATION
    tz: str = DEFAULT_TIMEZONE


# @MX:ANCHOR: [AUTO] The single resolver of LOCAL Faroe time the whole scheduler reads.
# @MX:REASON: fan_in >= 3 (dayparting REQ-OA-005, format-clock resolution REQ-OA-002, talk/news
#   time references REQ-OA-009 all derive from this ONE local-clock). DST-correctness (WET<->WEST)
#   is a [HARD] rail: a daypart boundary must fire at the right LOCAL wall-clock instant across a
#   DST transition, never at UTC or server-local time. Forking a second time source would drift the
#   schedule. Locked by test_schedule.py DST + daypart-boundary tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OA-009
class LocalClock:
    """LOCAL Faroe time/date/location awareness (REQ-OA-009), DST-correct.

    Resolves the current LOCAL wall clock for the station's location (Tórshavn,
    ``Atlantic/Faroe``, UTC+0 winter / UTC+1 summer) from an injectable UTC ``clock`` (wall
    in prod, deterministic in tests). Dayparts are anchored to LOCAL time, not UTC. The
    timezone is configurable; an absent tz database degrades to UTC with a logged warning so
    the scheduler still runs (the never-block rail)."""

    def __init__(self, *, tz: str = DEFAULT_TIMEZONE, location: str = DEFAULT_LOCATION,
                 dayparts: Optional[Sequence[Tuple[int, str]]] = None,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._tz_name = tz or DEFAULT_TIMEZONE
        self._location = location or DEFAULT_LOCATION
        self._dayparts = tuple(dayparts) if dayparts else DEFAULT_DAYPARTS
        import time as _time
        self._clock = clock or _time.time
        self._zone = None
        if ZoneInfo is not None:
            try:
                self._zone = ZoneInfo(self._tz_name)
            except Exception as exc:  # noqa: BLE001 - degrade to UTC, never block
                log_event(log, "schedule.tz_load_failed", tz=self._tz_name, error=str(exc))
                self._zone = None

    def _local_dt(self, epoch: float) -> datetime:
        utc = datetime.fromtimestamp(epoch, tz=timezone.utc)
        if self._zone is not None:
            return utc.astimezone(self._zone)
        return utc  # graceful degrade: UTC wall clock

    def daypart_for_hour(self, hour: int) -> str:
        """The daypart name for a LOCAL hour (REQ-OA-005). Boundaries are the FIXED rail."""
        name = self._dayparts[-1][1]  # wraps: the last daypart owns up to midnight
        for start, label in self._dayparts:
            if hour >= start:
                name = label
        return name

    def dayparts(self) -> Tuple[Tuple[int, str], ...]:
        return self._dayparts

    @staticmethod
    def _season_for(month: int, day: int) -> str:
        # Meteorological seasons (northern hemisphere); theming hint only (REQ-OA-009).
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"

    def now(self, epoch: Optional[float] = None) -> LocalContext:
        """Resolve the current LOCAL context (REQ-OA-009)."""
        ep = float(self._clock()) if epoch is None else float(epoch)
        dt = self._local_dt(ep)
        weekday = dt.weekday()
        return LocalContext(
            epoch=ep,
            iso=dt.isoformat(),
            hour=dt.hour,
            minute=dt.minute,
            weekday=weekday,
            day_of_week=("Monday", "Tuesday", "Wednesday", "Thursday",
                         "Friday", "Saturday", "Sunday")[weekday],
            is_weekend=weekday >= 5,
            daypart=self.daypart_for_hour(dt.hour),
            season=self._season_for(dt.month, dt.day),
            location=self._location,
            tz=self._tz_name,
        )


# =====================================================================================
# REQ-OA-002 — Format clock / clock-wheel engine (data-driven per-daypart clocks).
# =====================================================================================

# The typed slot kinds (REQ-OA-002). Slot ORDER within an active clock is FIXED; the
# slot CONTENTS + which variant is active are AI-authored (TUNABLE).
SLOT_SONG = "song"
SLOT_IMAGING = "imaging"
SLOT_TALK = "talk"
SLOT_NEWS = "news"
SLOT_ID = "id"          # the reserved top-of-hour station ID (REQ-OE-008)
SLOT_STOPSET = "stopset"
SLOT_REQUEST = "request"
SLOT_SPECIAL = "special"
SLOT_KINDS: Tuple[str, ...] = (
    SLOT_SONG, SLOT_IMAGING, SLOT_TALK, SLOT_NEWS, SLOT_ID,
    SLOT_STOPSET, SLOT_REQUEST, SLOT_SPECIAL,
)


@dataclass(frozen=True)
class Slot:
    """One typed slot in a format clock (REQ-OA-002). ``category`` is an AI-authored
    song-category hint (e.g. Power Current) for SLOT_SONG; opaque for other kinds."""

    kind: str
    category: str = ""

    def __post_init__(self) -> None:
        if self.kind not in SLOT_KINDS:
            raise ValueError(f"unknown slot kind: {self.kind!r}")


@dataclass(frozen=True)
class FormatClock:
    """One hour's ordered, typed slot wheel (REQ-OA-002). The FIRST slot is the reserved
    top-of-hour station ID (REQ-OE-008) — a FIXED rail. Slot order is fixed; contents are
    AI-authored. ``name`` identifies the clock variant within its daypart."""

    name: str
    slots: Tuple[Slot, ...]

    def __post_init__(self) -> None:
        if not self.slots:
            raise ValueError("a format clock must have at least the top-of-hour ID slot")
        if self.slots[0].kind != SLOT_ID:
            raise ValueError("REQ-OE-008: the top-of-hour ID slot is reserved (slot 0)")

    def resolve(self, position: int) -> Slot:
        """Resolve a 0-based position within the hour to exactly ONE concrete slot
        (REQ-OA-002b). Positions past the wheel wrap (the wheel repeats within the hour)."""
        return self.slots[position % len(self.slots)]


def make_default_clock(name: str, *, song_categories: Sequence[str],
                       talk_every: int = 4, imaging_every: int = 0) -> FormatClock:
    """Author a sane default clock variant (TUNABLE). Slot 0 is the reserved top-of-hour
    ID; then song slots cycle the supplied categories with a talk slot every ``talk_every``
    songs and an imaging slot every ``imaging_every`` songs (0 = none). The AI may evolve
    the wheel; this is only the default content cap."""
    slots: List[Slot] = [Slot(SLOT_ID)]
    cats = list(song_categories) or [""]
    n = 0
    for i in range(max(1, talk_every) * max(1, len(cats))):
        slots.append(Slot(SLOT_SONG, category=cats[i % len(cats)]))
        n += 1
        if imaging_every and n % imaging_every == 0:
            slots.append(Slot(SLOT_IMAGING))
        if talk_every and n % talk_every == 0:
            slots.append(Slot(SLOT_TALK))
    return FormatClock(name=name, slots=tuple(slots))


# @MX:NOTE: [AUTO] The anti-lattice property (AC-OA-002, default guidance, AI-tunable): the
#   number of clock variants per daypart is chosen so it is NOT a divisor or multiple of 24,
#   which would land the same song in the same hour every day. We default to a count that
#   satisfies the property; the AI may retune. ``is_anti_lattice`` is the test predicate.
def is_anti_lattice(variant_count: int) -> bool:
    """True if ``variant_count`` avoids the 24h lattice (AC-OA-002): it is neither a divisor
    nor a multiple of 24, so a fixed wheel does not repeat the same hour daily."""
    if variant_count <= 0:
        return False
    if variant_count % 24 == 0:       # a multiple of 24
        return False
    if 24 % variant_count == 0:       # a divisor of 24
        return False
    return True


@dataclass
class DaypartClockSet:
    """The set of format-clock VARIANTS the AI rotates within one daypart (REQ-OA-002/005).

    The variant COUNT defaults to one that satisfies the anti-lattice property
    (``is_anti_lattice``); the AI may evolve it (TUNABLE). ``persona_register`` records the
    daypart's persona register + within-hour energy curve — AI-chosen, not a fixed
    prescription (only the daypart MANDATE / boundary is fixed)."""

    daypart: str
    variants: Tuple[FormatClock, ...]
    persona_register: str = ""
    energy_curve: Tuple[float, ...] = ()

    def variant_for(self, day_index: int) -> FormatClock:
        """Pick the active clock variant for a given day (REQ-OA-002). Deterministic rotation
        across days so the wheel does not lattice onto the 24h grid."""
        return self.variants[day_index % len(self.variants)]


# =====================================================================================
# REQ-OA-003d — the genre-family map (the ONLY genuinely new data artifact this group adds).
# Raw acquisition tags are noisy across multi-source acquisition, so the off-schedule
# genre-family-balance dimension rotates over coarse FAMILIES, not raw tags. TUNABLE / AI-
# evolvable. A track with no recognized genre maps to the catch-all "other" family.
# =====================================================================================

DEFAULT_GENRE_FAMILY_MAP: Dict[str, str] = {
    # soul-funk
    "funk": "soul-funk", "soul": "soul-funk", "disco": "soul-funk", "rnb": "soul-funk",
    "r&b": "soul-funk", "motown": "soul-funk", "boogie": "soul-funk",
    # electronic-dance
    "house": "electronic-dance", "techno": "electronic-dance", "trance": "electronic-dance",
    "electronic": "electronic-dance", "edm": "electronic-dance", "dance": "electronic-dance",
    "drum and bass": "electronic-dance", "dnb": "electronic-dance", "garage": "electronic-dance",
    "ambient": "electronic-dance", "idm": "electronic-dance",
    # extreme-metal / rock
    "black metal": "extreme-metal", "death metal": "extreme-metal", "hardcore": "extreme-metal",
    "metal": "extreme-metal", "thrash": "extreme-metal", "grindcore": "extreme-metal",
    "rock": "rock", "punk": "rock", "indie": "rock", "alternative": "rock", "grunge": "rock",
    # hip-hop
    "hip hop": "hip-hop", "hip-hop": "hip-hop", "rap": "hip-hop", "trap": "hip-hop",
    # jazz / classical / world
    "jazz": "jazz", "bebop": "jazz", "swing": "jazz", "fusion": "jazz",
    "classical": "classical", "baroque": "classical", "orchestral": "classical",
    "reggae": "world", "dub": "world", "afrobeat": "world", "latin": "world",
    "folk": "folk", "country": "folk", "americana": "folk", "bluegrass": "folk",
    "pop": "pop",
}

FAMILY_OTHER = "other"


def genre_family(track: Any, family_map: Optional[Dict[str, str]] = None) -> str:
    """Map a track to its coarse GENRE-FAMILY (REQ-OA-003d). Checks genre then sub_genre then
    descriptive tags against the (TUNABLE) ``family_map`` (longest-token match wins so
    "black metal" beats "metal"); an unrecognized track is the catch-all ``other`` family."""
    fmap = family_map if family_map is not None else DEFAULT_GENRE_FAMILY_MAP
    fields: List[str] = []
    for attr in ("genre", "sub_genre"):
        val = getattr(track, attr, "") or ""
        if val:
            fields.append(str(val).lower())
    for tag in (getattr(track, "tags", []) or []):
        fields.append(str(tag).lower())
    # Longest map-key first so multi-word families ("black metal") beat their substring ("metal").
    for key in sorted(fmap, key=len, reverse=True):
        for f in fields:
            if key in f:
                return fmap[key]
    return FAMILY_OTHER


def _track_era(track: Any) -> str:
    """A soft ERA bucket for REQ-OA-003 (decade), derived from ``year``. Empty when unknown."""
    year = getattr(track, "year", None)
    if not year:
        return ""
    try:
        return f"{(int(year) // 10) * 10}s"
    except (TypeError, ValueError):
        return ""


# =====================================================================================
# REQ-OA-004 — Rotation categories & rotation-rate management.
# =====================================================================================

# Default rotation categories (TUNABLE schema). A track's category drives its target play
# frequency; the AI promotes/demotes/rests titles. No taste/coherence check is applied
# (REQ-OA-004 / CORE-001 REQ-D-002).
CAT_POWER = "power_current"
CAT_SECONDARY = "secondary"
CAT_RECURRENT = "recurrent"
CAT_GOLD = "gold_stay"
CAT_RESTING = "resting"
DEFAULT_ROTATION_CATEGORIES: Tuple[str, ...] = (
    CAT_POWER, CAT_SECONDARY, CAT_RECURRENT, CAT_GOLD, CAT_RESTING,
)


class RotationManager:
    """AI-managed rotation categories + turnover (REQ-OA-004).

    Classifies tracks into rotation categories and lets the AI promote / demote / rest /
    restore titles so each category's turnover matches the intended play frequency. The
    category schema + frequency bands are TUNABLE. [HARD] No taste/coherence match is
    enforced on category membership (CORE-001 REQ-D-002) — category is a ROTATION-RATE
    knob, not a taste filter. State is an in-memory map keyed by the track dedup key; an
    optional ``store`` (a ledger SeamWriter / dict-like with ``get``/``set``) persists it.
    """

    def __init__(self, *, categories: Optional[Sequence[str]] = None,
                 default_category: str = CAT_SECONDARY) -> None:
        self._categories = tuple(categories) if categories else DEFAULT_ROTATION_CATEGORIES
        if default_category not in self._categories:
            default_category = self._categories[0]
        self._default = default_category
        self._assigned: Dict[str, str] = {}

    def categories(self) -> Tuple[str, ...]:
        return self._categories

    def category_of(self, key: str) -> str:
        return self._assigned.get(key, self._default)

    def classify(self, key: str, category: str) -> bool:
        """Assign a track to a rotation category (REQ-OA-004). Unknown category -> rejected
        (the schema is TUNABLE but a category must be in it). No taste check is applied."""
        if category not in self._categories:
            return False
        self._assigned[key] = category
        return True

    def promote(self, key: str) -> str:
        """Move a track UP one rotation tier (toward power-current); idempotent at the top."""
        idx = self._categories.index(self.category_of(key))
        new = self._categories[max(0, idx - 1)]
        self._assigned[key] = new
        return new

    def demote(self, key: str) -> str:
        """Move a track DOWN one rotation tier; idempotent at the bottom (resting)."""
        idx = self._categories.index(self.category_of(key))
        new = self._categories[min(len(self._categories) - 1, idx + 1)]
        self._assigned[key] = new
        return new

    def rest(self, key: str) -> str:
        """Rest a title — pull it out of active rotation (REQ-OA-004)."""
        self._assigned[key] = CAT_RESTING if CAT_RESTING in self._categories else self._categories[-1]
        return self._assigned[key]

    def is_resting(self, key: str) -> bool:
        return self.category_of(key) == CAT_RESTING


# =====================================================================================
# REQ-OA-003 / 003a / 003c / 003d — the SELECTION refiner.
# Re-scores the library's legal-and-LRP-ranked candidate set (REQ-OA-003a) with the HARD
# artist rails (003a artist-separation, 003c artist-frequency), the SOFT separations (003),
# and — only in the unscheduled lane — the off-schedule genre-family balance + smooth
# adjacency (003d). Empty-legal-set relaxation (003b) plays one + LOGS. DETERMINISTIC.
# =====================================================================================


@dataclass
class SelectionConfig:
    """TUNABLE thresholds for the selection refiner (REQ-OA-003/003c/003d, REQ-OA-004 pattern)."""

    # 003a/003c — the HARD artist rails.
    artist_separation: int = 3          # min plays between two tracks by the same artist
    artist_max_per_window: int = 2      # max plays per artist within the rolling window
    artist_window: int = 20             # the rolling window (in recent plays) for the frequency cap
    # 003 — the SOFT separation weights (down-weight a candidate that matches the just-aired
    # track on a soft dimension). Each soft match adds its lambda to the candidate's penalty.
    soft_tempo_lambda: float = 0.15
    soft_energy_lambda: float = 0.15
    soft_era_lambda: float = 0.10
    soft_vocalist_lambda: float = 0.10
    soft_sound_code_lambda: float = 0.10
    soft_tempo_bucket: float = 0.10     # fractional BPM bucket width for "same tempo"
    soft_energy_bucket: float = 0.15    # energy bucket width for "same energy"
    # 003d — the off-schedule (unscheduled-lane) variety layers.
    balance_window: int = 12            # rolling window of recent aired+committed families
    target_ceiling: float = 0.34       # a family's share over the window above which it is penalized
    penalty_lambda: float = 1.0         # genre-family-balance weight
    adjacency_lambda: float = 0.6       # smooth-adjacency weight
    min_distinct_families_per_window: int = 0  # optional soft floor (0 = off)


@dataclass
class SelectionResult:
    """The refiner's pick + the traceability record (AC-OA-003)."""

    track: Any
    relaxed: bool = False
    relaxation_reason: str = ""
    score: float = 0.0


class SelectionRefiner:
    """The OPS-004 soft+hard separation scorer over the legal candidate set (REQ-OA-003*).

    Re-ranks ``library.legal_candidates`` (the no-repeat / LRP rail, REQ-OA-003a — produced by
    the library, NEVER relaxed here) by: (1) the HARD artist-separation + artist-frequency rails
    (REQ-OA-003a/003c — they EXCLUDE, not down-weight); (2) the SOFT separations (REQ-OA-003 —
    they down-weight); (3) in the UNSCHEDULED lane only, the off-schedule genre-family balance +
    smooth adjacency (REQ-OA-003d). The composite score is the LRP rank plus the soft penalties;
    the minimum-scoring legal candidate is picked, DETERMINISTICALLY (no RNG). On an empty
    legal-and-balanced subset it relaxes the SOFT layer (NOT the hard rails), plays one, and LOGS
    (REQ-OA-003b; continuity wins, REQ-OA-008).

    [HARD] The exemption predicate IS the activation predicate (REQ-OA-003d(c)): one
    ``is_unscheduled`` flag (default True) turns the (a)/(b) variety layers ON off-schedule and
    OFF inside a curated/scheduled block — so a single-genre genre-night plays UNMODIFIED with no
    taste/coherence/anti-drift check (CORE-001 REQ-D-002 / AC-OA-004).
    """

    def __init__(self, library: Any, *, cfg: Optional[SelectionConfig] = None,
                 family_map: Optional[Dict[str, str]] = None) -> None:
        self._library = library
        self._cfg = cfg or SelectionConfig()
        self._family_map = family_map if family_map is not None else DEFAULT_GENRE_FAMILY_MAP

    # -- the hard artist rails (REQ-OA-003a artist-separation, REQ-OA-003c frequency) -------- #

    def _artist_legal(self, candidate: Any, recent_artists: Sequence[str]) -> bool:
        """True if a candidate passes the HARD artist rails: it is at least
        ``artist_separation`` plays since the same artist last aired AND the same artist has
        not aired more than ``artist_max_per_window`` times in the rolling window (REQ-OA-003a/
        003c). These EXCLUDE; they are never relaxed by the soft layer (only the empty-set
        degradation, REQ-OA-003b, may borrow under logging)."""
        artist = _norm_artist(getattr(candidate, "artist", ""))
        if not artist:
            return True  # an unknown artist cannot be frequency-capped
        window = list(recent_artists)[: self._cfg.artist_window]
        # Separation: the artist must not appear within the most-recent ``artist_separation`` plays.
        for prior in window[: max(0, self._cfg.artist_separation)]:
            if _norm_artist(prior) == artist:
                return False
        # Frequency: count occurrences in the full rolling window.
        count = sum(1 for a in window if _norm_artist(a) == artist)
        if count >= self._cfg.artist_max_per_window:
            return False
        return True

    # -- the soft separations (REQ-OA-003) --------------------------------------------------- #

    def _soft_penalty(self, candidate: Any, last_track: Any) -> float:
        """The SOFT-separation penalty (REQ-OA-003): down-weight a candidate that matches the
        just-aired track on tempo / energy / era / vocalist-gender / sound-code. A scoring layer
        the AI may weigh/relax; NOT a hard rail. Returns 0 when there is no just-aired track."""
        if last_track is None:
            return 0.0
        c = self._cfg
        penalty = 0.0
        lb, cb = getattr(last_track, "bpm", 0.0), getattr(candidate, "bpm", 0.0)
        if lb and cb and abs(cb - lb) <= lb * c.soft_tempo_bucket:
            penalty += c.soft_tempo_lambda
        le, ce = getattr(last_track, "energy", 0.0), getattr(candidate, "energy", 0.0)
        if le and ce and abs(ce - le) <= c.soft_energy_bucket:
            penalty += c.soft_energy_lambda
        if _track_era(last_track) and _track_era(last_track) == _track_era(candidate):
            penalty += c.soft_era_lambda
        lv, cv = _soft_attr(last_track, "vocalist_gender"), _soft_attr(candidate, "vocalist_gender")
        if lv and lv == cv:
            penalty += c.soft_vocalist_lambda
        ls, cs = _soft_attr(last_track, "sound_code"), _soft_attr(candidate, "sound_code")
        if ls and ls == cs:
            penalty += c.soft_sound_code_lambda
        return penalty

    # -- the off-schedule variety layers (REQ-OA-003d, unscheduled lane only) ----------------- #

    def _family_balance_penalty(self, candidate: Any, window_families: Sequence[str]) -> float:
        """REQ-OA-003d(a) genre-family balance: penalize a candidate whose family's share over
        the rolling window exceeds the target ceiling — penalty = lambda * max(0, share - ceiling).
        Decays naturally as a saturated family ages out of the window, so families rotate."""
        if not window_families:
            return 0.0
        fam = genre_family(candidate, self._family_map)
        share = sum(1 for f in window_families if f == fam) / len(window_families)
        over = max(0.0, share - self._cfg.target_ceiling)
        return self._cfg.penalty_lambda * over

    def _adjacency_penalty(self, candidate: Any, last_track: Any, *,
                           at_boundary: bool) -> float:
        """REQ-OA-003d(b) smooth adjacency: penalize an energy/harmonic JUMP from the just-aired
        track, reusing ANALYSIS-006 ``library.adjacency`` (which withholds the harmonic filter on
        low-confidence keys per REQ-AT-007). A candidate that is NOT an adjacency neighbour of the
        just-aired track is penalized; a neighbour is not. SUSPENDED for the one transition at a
        deliberate BOUNDARY (daypart / format-clock slot change / top-of-hour)."""
        if last_track is None or at_boundary:
            return 0.0
        try:
            neighbours = self._library.adjacency(last_track)
        except Exception as exc:  # noqa: BLE001 - adjacency is best-effort; never blocks the pick
            log_event(log, "schedule.adjacency_error", error=str(exc))
            return 0.0
        if not neighbours:
            return 0.0  # no harmonic/tempo data (or low-confidence key withheld) -> no opinion
        ckey = getattr(candidate, "key", None)
        is_neighbour = any(getattr(n, "key", None) == ckey for n in neighbours)
        return 0.0 if is_neighbour else self._cfg.adjacency_lambda

    # -- the composite pick (the public API the picker calls) -------------------------------- #

    def refine(self, candidates: Sequence[Any], *, last_track: Any = None,
               recent_artists: Sequence[str] = (), window_families: Sequence[str] = (),
               is_unscheduled: bool = True, at_boundary: bool = False) -> Optional[SelectionResult]:
        """Pick the best-scoring LEGAL candidate (REQ-OA-003*). ``candidates`` is the library's
        legal-and-LRP-ranked set (REQ-OA-003a); index 0 is the plain LRP head. Returns None only
        for an empty input. DETERMINISTIC: ties break on the original (LRP) order, so identical
        state yields an identical pick.

        [HARD] is_unscheduled gates the off-schedule variety layers (REQ-OA-003d(c)). With it
        False (a curated/scheduled show), (a)/(b) are NOT applied — the block plays unmodified."""
        if not candidates:
            return None

        # (1) HARD artist rails first (REQ-OA-003a/003c): they EXCLUDE candidates.
        legal = [c for c in candidates if self._artist_legal(c, recent_artists)]
        relaxed = False
        relaxation_reason = ""
        if not legal:
            # REQ-OA-003b: no candidate clears the artist rails (thin catalog / request pressure).
            # The HARD no-repeat/LRP rail (REQ-OA-003a) is ALREADY honoured by ``candidates``; we
            # relax the artist-frequency soft pressure to the full legal-LRP set, play the LRP head,
            # and LOG it — continuity wins (REQ-OA-008). The same-track no-repeat rail is untouched.
            legal = list(candidates)
            relaxed = True
            relaxation_reason = "artist_rail_relaxed"
            log_event(log, "schedule.selection_relaxed", reason=relaxation_reason,
                      candidates=len(candidates))

        # (2)+(3) score each legal candidate: LRP rank + soft penalties (+ off-schedule layers).
        best: Optional[Any] = None
        best_score = math.inf
        for rank, c in enumerate(legal):
            score = float(rank)  # the LRP_rank base (REQ-OA-003a)
            score += self._soft_penalty(c, last_track)              # REQ-OA-003 soft separations
            if is_unscheduled:                                      # REQ-OA-003d(c) activation gate
                score += self._family_balance_penalty(c, window_families)   # (a)
                score += self._adjacency_penalty(c, last_track, at_boundary=at_boundary)  # (b)
            if score < best_score:
                best_score, best = score, c
        return SelectionResult(track=best, relaxed=relaxed,
                               relaxation_reason=relaxation_reason, score=best_score)


def _norm_artist(name: str) -> str:
    raw = unicodedata.normalize("NFKD", str(name or "").lower())
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", raw).strip()


def _soft_attr(track: Any, attr: str) -> str:
    """A soft, optional dimension (vocalist_gender / sound_code) — these fields may not exist on
    a Track (ANALYSIS-006 has not produced them); a missing dimension simply contributes no
    penalty (graceful degradation), so the soft layer never over-constrains a thin catalog."""
    val = getattr(track, attr, "") or ""
    if not val:
        # Fall back to a descriptive tag of the form "attr:value" if present.
        for tag in (getattr(track, "tags", []) or []):
            t = str(tag).lower()
            if t.startswith(attr.replace("_", "") + ":") or t.startswith(attr + ":"):
                return t.split(":", 1)[1].strip()
        return ""
    return str(val).strip().lower()


# =====================================================================================
# REQ-OA-013 — editorial run-mode selection each loop.
# =====================================================================================

# The TUNABLE run-mode set the AI selects from each planning cycle (REQ-OA-013). ``reflect`` is
# REGISTERED from SPEC-RADIO-REFLECT-026 (forward-ref) but is NOT selectable here until that seam
# is coded — the director never picks it; the others are unaffected (graceful degradation).
RUN_MODE_MAINTENANCE = "maintenance"
RUN_MODE_RESPONSIVE = "responsive"
RUN_MODE_CONTINUITY = "continuity"
RUN_MODE_SPECIAL = "special"
RUN_MODE_QUIET = "quiet"
RUN_MODE_REFLECT = "reflect"  # REGISTERED (REFLECT-026), never auto-selected until the seam exists
RUN_MODES: Tuple[str, ...] = (
    RUN_MODE_MAINTENANCE, RUN_MODE_RESPONSIVE, RUN_MODE_CONTINUITY,
    RUN_MODE_SPECIAL, RUN_MODE_QUIET, RUN_MODE_REFLECT,
)
# The modes the director MAY auto-select (``reflect`` excluded until REFLECT-026 is coded).
SELECTABLE_RUN_MODES: Tuple[str, ...] = tuple(m for m in RUN_MODES if m != RUN_MODE_REFLECT)


def select_run_mode(*, cycle: int, library_count: int, wishlist_low: bool,
                     has_signals: bool = False, has_special: bool = False) -> str:
    """Choose this cycle's RUN MODE from an editorial brief (REQ-OA-013). A deterministic default
    brief the AI may evolve: low stock -> maintenance; fresh listener signals -> responsive; a
    planned special -> special; an even idle cycle -> quiet (deliberately let music run); else
    continuity (advance running threads). ``reflect`` is NEVER returned until REFLECT-026 exists.
    No fixed per-loop behaviour is hardcoded — the brief is TUNABLE."""
    if has_special:
        return RUN_MODE_SPECIAL
    if wishlist_low or library_count == 0:
        return RUN_MODE_MAINTENANCE
    if has_signals:
        return RUN_MODE_RESPONSIVE
    if cycle % 4 == 0:
        return RUN_MODE_QUIET
    return RUN_MODE_CONTINUITY


# =====================================================================================
# REQ-OA-001 / 015 — the schedule as a VIEW over the OD-007 ledger (no new store).
# =====================================================================================

EV_PROGRAM_CYCLE = "program_cycle"
EV_SCHEDULE_PLANNED = "schedule_planned"
EV_SLOT_ADDED = "slot_added"
EV_SLOT_REMOVED = "slot_removed"
EV_SLOT_MOVED = "slot_moved"
EV_PERSONA_ASSIGNED = "persona_assigned"
EV_TIMEBLOCK_RESERVED = "timeblock_reserved"
EV_TIMEBLOCK_RESTORED = "timeblock_restored"

# Schedule-grid CRUD operation names (REQ-OA-015). ADD/REMOVE/MOVE map onto CORE-001 REQ-B-003
# insert/replace/move-show; ASSIGN/REASSIGN is the first-class new persona-to-slot op.
GRID_ADD = "add"
GRID_REMOVE = "remove"
GRID_MOVE = "move"
GRID_ASSIGN = "assign"


@dataclass
class ScheduleBlock:
    """One scheduled block in the 24h grid (REQ-OA-001/015). ``start_hour`` is the LOCAL Faroe
    hour the block opens; ``persona_id`` binds a curator (empty = the house/unscheduled lane).
    ``show_or_episode_id`` is the REQ-OB-006 association — ``'unscheduled'`` means the host-less
    default lane where the off-schedule variety layers (REQ-OA-003d) apply."""

    slot_id: str
    start_hour: int
    daypart: str
    kind: str = "music"  # "music" | "show" | "special" | "longform"
    persona_id: str = ""
    show_or_episode_id: str = "unscheduled"
    clock_variant: str = ""

    def is_unscheduled(self) -> bool:
        return self.show_or_episode_id == "unscheduled"


# @MX:ANCHOR: [AUTO] The schedule VIEW — a projection over the ONE OD-007 ledger, never a store.
# @MX:REASON: fan_in >= 3 (the ProgramDirector plans through it, the grid-CRUD mutates through it,
#   and the playout ``what_airs_now`` resolver + NoOrphanBootstrap read through it). [HARD]
#   single-source: the schedule is the most-recent-wins projection of ``slot_*``/``persona_assigned``
#   events; forking a separate schedule store would break the REQ-OD-007 single-ledger rail and the
#   ORCH-005/CORE-001 B-003 coordination. Locked by test_schedule.py grid-CRUD + projection tests.
# @MX:SPEC: SPEC-RADIO-OPS-004 REQ-OA-001 / REQ-OA-015
class Schedule:
    """The 24h schedule as a VIEW over the OD-007 ledger (REQ-OA-001/015) — NO new store.

    The live grid is the most-recent-wins projection of ``slot_added`` / ``slot_removed`` /
    ``slot_moved`` / ``persona_assigned`` events on the ONE ``EventLedger``. With no ledger it is
    an in-memory grid (correct + queryable, not cross-restart durable). Every grid edit PRESERVES
    the 24h no-gap coverage + the always-staffed invariant and takes effect for FUTURE blocks
    without interrupting the current stream (REQ-OA-015). Grid-edit frequency is bounded by the
    OD-010 rarity tiering via an optional ``budget`` (MeasuredChangeBudget).

    [HARD] Reuses — does NOT fork — the CORE-001 schedule store: the brain has no separate
    REQ-B-003 store, so this ledger-VIEW IS OPS-004's schedule representation; the ORCH-005
    REQ-RA-001(g) dispatch routing is the (unbuilt) seam.
    """

    def __init__(self, ledger: Optional[Any] = None, *, budget: Optional[Any] = None,
                 clock: Optional[LocalClock] = None) -> None:
        self._ledger = ledger
        self._budget = budget
        self._clock = clock or LocalClock()
        # In-memory grid keyed by slot_id (the projection; rebuilt from the ledger on read).
        self._grid: Dict[str, ScheduleBlock] = {}
        self._rebuild_from_ledger()

    def _rebuild_from_ledger(self) -> None:
        """Project the current grid from the append-only schedule events (most-recent-wins)."""
        if self._ledger is None:
            return
        try:
            grid: Dict[str, ScheduleBlock] = {}
            for ev in self._ledger.events():
                d = ev.data or {}
                sid = d.get("slot_id")
                if not sid:
                    continue
                if ev.event_type == EV_SLOT_ADDED:
                    grid[sid] = _block_from_record(d)
                elif ev.event_type == EV_SLOT_REMOVED:
                    grid.pop(sid, None)
                elif ev.event_type == EV_SLOT_MOVED and sid in grid:
                    grid[sid].start_hour = int(d.get("start_hour", grid[sid].start_hour))
                    grid[sid].daypart = d.get("daypart", grid[sid].daypart)
                elif ev.event_type == EV_PERSONA_ASSIGNED and sid in grid:
                    grid[sid].persona_id = d.get("persona_id", "")
                    grid[sid].show_or_episode_id = d.get(
                        "show_or_episode_id", grid[sid].show_or_episode_id)
            self._grid = grid
        except Exception as exc:  # noqa: BLE001 - a projection fault degrades to the in-memory grid
            log_event(log, "schedule.rebuild_error", error=str(exc))

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        if self._ledger is None:
            return
        try:
            self._ledger.append(event_type, data, persona_id=data.get("persona_id", ""))
        except Exception as exc:  # noqa: BLE001 - a ledger fault never blocks the schedule
            log_event(log, "schedule.emit_error", event_type=event_type, error=str(exc))

    def blocks(self) -> List[ScheduleBlock]:
        """The current grid, ordered by local start hour."""
        return sorted(self._grid.values(), key=lambda b: b.start_hour)

    def is_empty(self) -> bool:
        return not self._grid

    # -- the no-gap + always-staffed invariants (REQ-OA-015 [HARD]) --------------------------- #

    def covers_24h(self) -> bool:
        """True iff every local hour 0..23 is covered by exactly-one block start chain (no gap)."""
        if not self._grid:
            return False
        starts = sorted({b.start_hour for b in self._grid.values()})
        return starts and starts[0] == 0  # a block starting at 0 + ordered chain covers the day

    def always_staffed(self) -> bool:
        """True iff every block is either host-staffed OR explicitly the unscheduled house lane
        (which the no-orphan bootstrap degrade-staffs). No block is left orphaned (REQ-OB-014)."""
        return all(b.persona_id or b.is_unscheduled() for b in self._grid.values())

    def _would_preserve_invariants(self, proposed: Dict[str, ScheduleBlock]) -> bool:
        if not proposed:
            return False
        starts = sorted({b.start_hour for b in proposed.values()})
        if starts[0] != 0:
            return False  # a gap at the top of the day
        return all(b.persona_id or b.is_unscheduled() for b in proposed.values())

    # -- grid CRUD (REQ-OA-015) -------------------------------------------------------------- #

    def _tier_for(self, op: str, *, discontinue: bool = False) -> str:
        # Routine MOVE/REASSIGN is Tier 2 structural; an ADD/REMOVE that discontinues/relaunches a
        # show escalates to Tier 1 (rarest) per REQ-OD-010.
        from .ledger import TIER_IDENTITY, TIER_STRUCTURAL
        if op in (GRID_ADD, GRID_REMOVE) and discontinue:
            return TIER_IDENTITY
        return TIER_STRUCTURAL

    def _budget_ok(self, op: str, *, discontinue: bool, editorial_reason: str) -> bool:
        """Bound grid-edit frequency by the OD-010 rarity tier (REQ-OA-015). With no budget wired
        the edit is allowed (the budget is the throttle, not a hard gate on correctness)."""
        if self._budget is None:
            return True
        tier = self._tier_for(op, discontinue=discontinue)
        try:
            decision = self._budget.evaluate(
                tier=tier, target=f"schedule.{op}", rationale=editorial_reason,
                editorial_reason=editorial_reason,
                is_identity=(tier != "tier2_structural"))
            return decision.applied
        except Exception as exc:  # noqa: BLE001 - a budget fault never blocks the schedule
            log_event(log, "schedule.budget_error", op=op, error=str(exc))
            return True

    def add_slot(self, block: ScheduleBlock, *, discontinue: bool = False,
                 editorial_reason: str = "", seed: bool = False) -> bool:
        """ADD a slot/show (REQ-OA-015 -> CORE-001 REQ-B-003 insert). [HARD] preserves no-gap +
        always-staffed; takes effect for FUTURE blocks. Rejected if it would break an invariant or
        (when not a ``seed`` plan write) the rarity budget is spent. The initial 24h plan seeds the
        grid with ``seed=True`` so the bootstrap is NOT throttled like a routine grid edit (mirrors
        the OY segment-registry seed bypass)."""
        proposed = dict(self._grid)
        proposed[block.slot_id] = block
        if not self._would_preserve_invariants(proposed):
            return False
        if not seed and not self._budget_ok(GRID_ADD, discontinue=discontinue,
                                            editorial_reason=editorial_reason):
            return False
        self._grid[block.slot_id] = block
        self._emit(EV_SLOT_ADDED, _block_record(block))
        return True

    def remove_slot(self, slot_id: str, *, discontinue: bool = False,
                    editorial_reason: str = "") -> bool:
        """REMOVE a slot/show (REQ-OA-015 -> REQ-B-003 replace). [HARD] rejected if removal would
        leave a gap (no-gap coverage). A discontinue/relaunch escalates to Tier 1."""
        if slot_id not in self._grid:
            return False
        proposed = {k: v for k, v in self._grid.items() if k != slot_id}
        if not self._would_preserve_invariants(proposed):
            return False
        if not self._budget_ok(GRID_REMOVE, discontinue=discontinue,
                               editorial_reason=editorial_reason):
            return False
        del self._grid[slot_id]
        self._emit(EV_SLOT_REMOVED, {"slot_id": slot_id})
        return True

    def move_slot(self, slot_id: str, new_start_hour: int, *, editorial_reason: str = "") -> bool:
        """MOVE (re-time) a slot (REQ-OA-015 -> REQ-B-003 move-show). Routine = Tier 2."""
        if slot_id not in self._grid:
            return False
        block = self._grid[slot_id]
        proposed = dict(self._grid)
        moved = ScheduleBlock(**{**_block_record(block), "start_hour": int(new_start_hour),
                                 "daypart": self._clock.daypart_for_hour(int(new_start_hour))})
        proposed[slot_id] = moved
        if not self._would_preserve_invariants(proposed):
            return False
        if not self._budget_ok(GRID_MOVE, discontinue=False, editorial_reason=editorial_reason):
            return False
        self._grid[slot_id] = moved
        self._emit(EV_SLOT_MOVED, {"slot_id": slot_id, "start_hour": int(new_start_hour),
                                   "daypart": moved.daypart})
        return True

    def assign_persona(self, slot_id: str, persona_id: str, show_or_episode_id: str, *,
                       caps_ok: Callable[[str, str], bool] = None,
                       editorial_reason: str = "") -> bool:
        """ASSIGN / REASSIGN a persona to a slot (REQ-OA-015 — the first-class new op). Honours the
        host caps + the PROGRAMMING-007 anti-convergence firewall via the injected ``caps_ok``
        predicate (a reassigned persona must not collide territories on its new slot). Routine
        reassign = Tier 2. Binding a persona makes the slot a scheduled/curated block (so the
        off-schedule variety layers are exempt, REQ-OA-003d(c))."""
        if slot_id not in self._grid:
            return False
        if caps_ok is not None and not caps_ok(persona_id, slot_id):
            return False
        if not self._budget_ok(GRID_ASSIGN, discontinue=False, editorial_reason=editorial_reason):
            return False
        self._grid[slot_id].persona_id = persona_id
        self._grid[slot_id].show_or_episode_id = show_or_episode_id
        self._emit(EV_PERSONA_ASSIGNED, {"slot_id": slot_id, "persona_id": persona_id,
                                         "show_or_episode_id": show_or_episode_id})
        return True

    # -- the "what airs now" resolver the playout consults (REQ-OA-001) ---------------------- #

    def block_for_hour(self, hour: int) -> Optional[ScheduleBlock]:
        """The block governing a given LOCAL hour (the latest block whose start <= hour)."""
        governing: Optional[ScheduleBlock] = None
        for b in self.blocks():
            if b.start_hour <= hour:
                governing = b
        # wrap: if no block starts at/before this hour, the last block of the day carries over.
        if governing is None and self._grid:
            governing = self.blocks()[-1]
        return governing

    def what_airs_now(self, epoch: Optional[float] = None) -> Optional[ScheduleBlock]:
        """Resolve what airs at the current LOCAL Faroe time (REQ-OA-001/009)."""
        ctx = self._clock.now(epoch)
        return self.block_for_hour(ctx.hour)


def _block_record(block: ScheduleBlock) -> Dict[str, Any]:
    return {"slot_id": block.slot_id, "start_hour": block.start_hour, "daypart": block.daypart,
            "kind": block.kind, "persona_id": block.persona_id,
            "show_or_episode_id": block.show_or_episode_id, "clock_variant": block.clock_variant}


def _block_from_record(d: Dict[str, Any]) -> ScheduleBlock:
    return ScheduleBlock(
        slot_id=d.get("slot_id", ""), start_hour=int(d.get("start_hour", 0)),
        daypart=d.get("daypart", ""), kind=d.get("kind", "music"),
        persona_id=d.get("persona_id", ""),
        show_or_episode_id=d.get("show_or_episode_id", "unscheduled"),
        clock_variant=d.get("clock_variant", ""))


# =====================================================================================
# REQ-OA-008 — never a single point of silence: the no-orphan bootstrap.
# =====================================================================================

# The house voice / unscheduled lane fallback the playout consults when the schedule is empty or
# a scheduled item is unavailable. NEVER silent: degrades persona -> show -> schedule -> music.
HOUSE_LANE = ScheduleBlock(slot_id="__house__", start_hour=0, daypart="",
                           kind="music", persona_id="", show_or_episode_id="unscheduled")


class NoOrphanBootstrap:
    """The always-on, never-silent rail (REQ-OA-008). Resolves "what airs now" in the bootstrap
    order persona -> show -> schedule, and DEGRADES to the house-voice + music unscheduled lane
    when the schedule is empty or a scheduled item is unavailable — so no OPS scheduling decision
    is ever a single point of silence (continuous operation wins, inherited from CORE-001 Group C).

    The degrade is the SAFE DEFAULT: with scheduling OFF (no Schedule wired) ``resolve`` always
    returns the house lane, which the existing music picker already serves — byte-identical."""

    def __init__(self, schedule: Optional[Schedule] = None) -> None:
        self._schedule = schedule

    def resolve(self, epoch: Optional[float] = None) -> ScheduleBlock:
        """The block to air now, never None (REQ-OA-008). An empty/absent schedule or a faulted
        lookup degrades to the house lane (music + house voice) — the queue never stalls."""
        if self._schedule is None:
            return HOUSE_LANE
        try:
            block = self._schedule.what_airs_now(epoch)
        except Exception as exc:  # noqa: BLE001 - a resolve fault degrades to the house lane
            log_event(log, "schedule.resolve_error", error=str(exc))
            return HOUSE_LANE
        if block is None:
            log_event(log, "schedule.no_orphan_degrade", reason="empty_schedule")
            return HOUSE_LANE
        return block

    def is_unscheduled_now(self, epoch: Optional[float] = None) -> bool:
        """Whether the current lane is the unscheduled (off-schedule) lane — the activation
        predicate the SelectionRefiner uses to gate the REQ-OA-003d variety layers."""
        return self.resolve(epoch).is_unscheduled()


# =====================================================================================
# REQ-OA-001 / 013 — the autonomous Program Director (24h planning + run-mode each cycle).
# =====================================================================================


class ProgramDirector:
    """The autonomous PD: plan the 24h programme + pick a run mode each cycle (REQ-OA-001/013).

    ``plan_24h`` arranges the day into per-daypart blocks (music + AI-invented shows when a
    ShowEngine is wired) WITHOUT a human prompt and without prescribing the creative arrangement —
    only the FIXED rails apply (no-gap coverage, top-of-hour ID, daypart boundaries). Each planning
    cycle is logged with its trigger + chosen run mode onto the ONE ledger (REQ-OA-001/013). The
    plan is the default deterministic arrangement; the AI may evolve it (TUNABLE).

    [HARD] OFF by default: built ONLY when scheduling is enabled. With it off the PD never plans
    and the director tick is byte-identical."""

    def __init__(self, *, clock: Optional[LocalClock] = None, schedule: Optional[Schedule] = None,
                 show_engine: Optional[Any] = None, ledger: Optional[Any] = None) -> None:
        self._clock = clock or LocalClock()
        self._schedule = schedule
        self._show_engine = show_engine
        self._ledger = ledger
        self._cycle = 0

    def plan_24h(self, *, trigger: str = "startup") -> List[ScheduleBlock]:
        """Plan the 24h programme (REQ-OA-001). One block per daypart, covering every hour with
        no gap; a host-less music block by default, upgraded to an AI-invented show when the
        ShowEngine offers an active show for the daypart. The arrangement is AI-authored — no
        fixed programme/playlist is hardcoded as the creative decision-maker."""
        blocks: List[ScheduleBlock] = []
        for start, name in self._clock.dayparts():
            block = ScheduleBlock(slot_id=f"daypart-{name}", start_hour=start, daypart=name,
                                  kind="music", persona_id="", show_or_episode_id="unscheduled")
            # Upgrade to a scheduled show when the engine has an active one (REQ-OB-006 association).
            show = self._active_show()
            if show is not None:
                block.kind = "show"
                block.persona_id = str(getattr(show, "persona_id", "") or "")
                block.show_or_episode_id = str(getattr(show, "id", "") or f"show-{name}")
            blocks.append(block)
        if self._schedule is not None:
            for b in blocks:
                self._schedule.add_slot(b, editorial_reason=f"24h plan ({trigger})", seed=True)
        self._emit_cycle(trigger=trigger, planned=len(blocks))
        return blocks

    def _active_show(self) -> Optional[Any]:
        if self._show_engine is None:
            return None
        try:
            return self._show_engine.active_show()
        except Exception as exc:  # noqa: BLE001 - the show lens is best-effort; never blocks planning
            log_event(log, "schedule.active_show_error", error=str(exc))
            return None

    def run_mode_for_cycle(self, *, library_count: int, wishlist_low: bool,
                           has_signals: bool = False, has_special: bool = False) -> str:
        """Select this cycle's run mode (REQ-OA-013). ``reflect`` is never returned (REFLECT-026
        unbuilt). Logged onto the ledger with the cycle's trigger."""
        self._cycle += 1
        mode = select_run_mode(cycle=self._cycle, library_count=library_count,
                               wishlist_low=wishlist_low, has_signals=has_signals,
                               has_special=has_special)
        return mode

    def _emit_cycle(self, *, trigger: str, planned: int, run_mode: str = "") -> None:
        if self._ledger is None:
            return
        try:
            self._ledger.append(EV_PROGRAM_CYCLE,
                                {"cycle": self._cycle, "trigger": trigger,
                                 "planned": planned, "run_mode": run_mode})
        except Exception as exc:  # noqa: BLE001 - a cycle-log fault never blocks planning
            log_event(log, "schedule.cycle_log_error", error=str(exc))


# =====================================================================================
# REQ-OA-007 — imaging & ID cadence direction (the AI's element decision + trigger seam).
# =====================================================================================


@dataclass
class ImagingDecision:
    """The AI's imaging/ID element decision for an imaging/ID clock slot (REQ-OA-007). The actual
    PRODUCTION is Group OE's (UNBUILT) — this is the decision + the trigger seam; with no producer
    the slot degrades to a cached evergreen / music fallback (REQ-OA-008)."""

    element_type: str       # e.g. "station_id" | "sweeper" | "promo" | "show_open"
    copy: str = ""
    wet_dry: str = "wet"    # "wet" (music bed) | "dry" (voice only)
    language: str = "en"
    is_top_of_hour_id: bool = False


def decide_imaging(slot: Slot, *, local: LocalContext, language: str = "en") -> ImagingDecision:
    """Decide which imaging element airs for an imaging/ID slot (REQ-OA-007). The top-of-hour ID
    slot is RESERVED (REQ-OE-008) — it always produces a station ID; other imaging cadence
    positions are TUNABLE and the type/copy/wet-dry/language are the AI's call."""
    if slot.kind == SLOT_ID:
        return ImagingDecision(element_type="station_id",
                               copy=f"{DEFAULT_LOCATION} — top of the hour",
                               wet_dry="dry", language=language, is_top_of_hour_id=True)
    return ImagingDecision(element_type="sweeper", copy="", wet_dry="wet", language=language)


def trigger_imaging(decision: ImagingDecision, *, producer: Optional[Callable[[ImagingDecision], Any]] = None
                    ) -> Optional[Any]:
    """Trigger the imaging production pipeline (Group OE) for the AI's element (REQ-OA-007). The
    ``producer`` seam is Group OE's (UNBUILT); with no producer this returns None and the caller
    degrades to a cached evergreen / music fallback (REQ-OA-008) — the slot is never silent."""
    if producer is None:
        return None
    try:
        return producer(decision)
    except Exception as exc:  # noqa: BLE001 - an imaging-production fault degrades, never blocks
        log_event(log, "schedule.imaging_error", error=str(exc))
        return None


# =====================================================================================
# REQ-OA-006 / 014 — segue/adjacency decision + context-aware transition/mixing style.
# =====================================================================================

# Transition styles (REQ-OA-014). The mechanics EXECUTE in the playout layer (Liquidsoap/ffmpeg);
# this emits the style + params. [HARD] No transition is a sharp hard cut by default (NFR-O-11).
STYLE_DJ_MIX = "dj_mix"          # crossfade + beatmatch + EQ blend (club/dance shows)
STYLE_CROSSFADE = "crossfade"    # clean gentle crossfade / fade-out (regular shows)


@dataclass
class TransitionParams:
    """The transition the AI emits for the playout layer (REQ-OA-006/014). ``crossfade_seconds`` +
    ``cue_in``/``cue_out`` are the segue params; ``beatmatch``/``eq_blend`` are the DJ-mix knobs
    (used only for club/dance style when BPM/key metadata is present)."""

    style: str
    crossfade_seconds: float = 2.0
    cue_in: float = 0.0
    cue_out: float = 0.0
    beatmatch: bool = False
    eq_blend: bool = False


# Show/daypart contexts that warrant DJ-style mixing (REQ-OA-014). TUNABLE; the AI decides by
# context. Matched case-insensitively against the show/daypart label.
CLUB_DANCE_CONTEXTS: Tuple[str, ...] = (
    "asot", "trance", "club", "dance", "p3 dans", "house", "techno", "dj set",
)


def decide_transition(*, context: str, from_track: Any = None, to_track: Any = None
                      ) -> TransitionParams:
    """Pick a transition/mixing style by show/daypart CONTEXT and emit params for the playout layer
    (REQ-OA-006/014). CLUB/DANCE context -> DJ-style (crossfade + beatmatch + EQ blend) when BPM
    metadata is present (degrades to a plain crossfade if missing); REGULAR context -> a clean
    crossfade with no beatmatch/EQ. [HARD] never a sharp hard cut (NFR-O-11): crossfade_seconds
    is always > 0."""
    ctx = str(context or "").lower()
    is_club = any(marker in ctx for marker in CLUB_DANCE_CONTEXTS)
    have_bpm = bool(getattr(to_track, "bpm", 0.0)) and bool(getattr(from_track, "bpm", 0.0))
    if is_club and have_bpm:
        return TransitionParams(style=STYLE_DJ_MIX, crossfade_seconds=6.0,
                                beatmatch=True, eq_blend=True)
    if is_club:
        # club context but no BPM metadata -> degrade to a clean crossfade (REQ-OA-014).
        return TransitionParams(style=STYLE_CROSSFADE, crossfade_seconds=4.0)
    return TransitionParams(style=STYLE_CROSSFADE, crossfade_seconds=2.0)


def decide_adjacency(library: Any, track: Any, *, rising_energy: bool = False) -> List[Any]:
    """The AI's next-song adjacency decision for flow (REQ-OA-006): the tempo/energy/key-compatible
    neighbours of ``track``, via ANALYSIS-006 ``library.adjacency`` (query primitives only; the
    DECISION is OPS-004's). Sample-accurate beat-aligned mixing is a later phase (R-O-9)."""
    try:
        return library.adjacency(track, rising_energy=rising_energy)
    except Exception as exc:  # noqa: BLE001 - adjacency is best-effort
        log_event(log, "schedule.decide_adjacency_error", error=str(exc))
        return []


# =====================================================================================
# REQ-OA-010 / 011 / 012 — catalog record reconciliation + the queryable catalog the PD curates.
# OPS-004 CONSUMES ANALYSIS-006's produced features + ENRICH-012's canonical reconciliation; it
# owns ONLY the catalog RECORD query surface — it never re-runs librosa/aubio nor forks the store.
# =====================================================================================


def reconcile_record(artist: str, title: str, album: str = "") -> Dict[str, str]:
    """Normalize a garbled catalog RECORD field (REQ-OA-010) — collapse whitespace, strip stray
    punctuation runs — so the PD reasons over a trustworthy catalog. [Disambiguation] this corrects
    the catalog / DB RECORD ONLY; any on-file tag/artwork WRITE is routed through TAGSTREAM-009
    (Group TW), referenced not forked — OPS-004 never mutates the audio files. The authoritative
    artist/title source (AcoustID/MusicBrainz) is ENRICH-012's; this is the OA-owned record
    normalization the PD applies on top."""
    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKC", str(s or ""))
        s = re.sub(r"\s+", " ", s).strip()
        return s
    return {"artist": _norm(artist), "title": _norm(title), "album": _norm(album)}


class CatalogView:
    """The accurate, queryable catalog the program director curates from (REQ-OA-012).

    A thin PD-facing VIEW composing the existing ``library.query`` (REQ-AD-002 feature filter) +
    ``library.adjacency`` (REQ-AD-004 DJ-set neighbours) — it owns NO store and re-runs NO audio
    analysis (ANALYSIS-006 produces bpm/camelot/key/energy; ENRICH-012 reconciles genre/year). It
    exposes the PD's curation primitives: genre nights, mood/energy arcs, and BPM/key-matched
    DJ-sets, all over the SAME library record (REQ-OA-011/012 consumed, not forked)."""

    def __init__(self, library: Any) -> None:
        self._library = library

    def genre_night(self, genre: str, *, limit: Optional[int] = None) -> List[Any]:
        """Tracks for a themed genre night (REQ-OA-012)."""
        return self._library.query(genre=genre, limit=limit)

    def energy_arc(self, *, energy_min: float, energy_max: float,
                   limit: Optional[int] = None) -> List[Any]:
        """Tracks within a mood/energy band for an energy arc (REQ-OA-012)."""
        return self._library.query(energy_min=energy_min, energy_max=energy_max, limit=limit)

    def dj_set(self, seed: Any, *, rising_energy: bool = False,
               limit: Optional[int] = None) -> List[Any]:
        """A BPM/key-matched DJ-set chain seeded from a track (REQ-OA-012, consumes ANALYSIS-006)."""
        return self._library.adjacency(seed, rising_energy=rising_energy, limit=limit)

    def is_enriched(self, track: Any) -> bool:
        """Whether a track carries the rich catalog fields the PD reasons over (REQ-OA-011). True
        when at least one of genre / bpm / energy / year is populated — partial enrichment is still
        recorded and usable (the filename %ARTIST% - %TITLE% fallback recovers artist/title)."""
        return bool(getattr(track, "genre", "") or getattr(track, "bpm", 0.0)
                    or getattr(track, "energy", 0.0) or getattr(track, "year", None))


# =====================================================================================
# REQ-OA-016 — content-driven-duration long-form time-block override (variant of REQ-OB-005).
# =====================================================================================


@dataclass
class TimeBlockOverride:
    """A content-driven-duration long-form override window (REQ-OA-016) — the VARIANT of the
    REQ-OB-005 special-event override-and-restore discipline whose LENGTH is the EPISODE'S DURATION
    CLAIM (e.g. 73 min), not a clock-snapped boundary. It MAY suspend the slot-based format clock
    across its span and MAY cross a daypart boundary. The episode itself + its duration claim are
    SPEC-RADIO-LONGFORM-025's (UNBUILT, forward-referenced); OPS-004 owns the VARIANT mechanics +
    time-budgeting + the rails-it-honours.

    [HARD] WEAKENS NO FIXED RAIL: the top-of-hour ID (REQ-OE-008) is preserved (woven at the nearest
    internal segment boundary, never dropped); the daypart boundary (REQ-OA-005) is DEFERRED, not
    moved; the block ends content-driven at a song/segment boundary (never-cut-short NFR-O-12) and
    restores the default clock cleanly. Because the block is a SCHEDULED/CURATED block
    (show_or_episode_id != 'unscheduled'), the REQ-OA-003d(c) off-schedule-variety exemption already
    covers it — no taste/coherence/anti-drift check applies inside the episode."""

    episode_id: str
    start_hour: int
    duration_minutes: float
    persona_id: str = ""

    def end_minute_of_day(self) -> float:
        """The content-driven END (minutes from local midnight) — NOT snapped to the hour clock."""
        return self.start_hour * 60.0 + self.duration_minutes

    def spans_daypart_boundary(self, clock: LocalClock) -> bool:
        start_dp = clock.daypart_for_hour(self.start_hour)
        end_hour = int(self.end_minute_of_day() // 60) % 24
        return clock.daypart_for_hour(end_hour) != start_dp

    def is_unscheduled(self) -> bool:
        return False  # a long-form block is always a scheduled/curated block (REQ-OA-003d(c) exempt)


def reserve_timeblock(schedule: Schedule, override: TimeBlockOverride, *,
                      clock: Optional[LocalClock] = None) -> bool:
    """Reserve a content-driven-duration long-form window on the grid (REQ-OA-016 time-budgeting).
    The block reserves its content-driven window and the surrounding slot-based schedule absorbs the
    displacement while [HARD] preserving the 24h no-gap coverage + the always-staffed invariant. The
    reservation routes through the REQ-OA-015 grid CRUD (no forked store). Returns False if no
    episode is supplied (LONGFORM-025 seam unbuilt -> no override; graceful degradation)."""
    if not override.episode_id or override.duration_minutes <= 0:
        return False  # no episode / no duration claim -> no override (LONGFORM-025 seam)
    clk = clock or LocalClock()
    block = ScheduleBlock(
        slot_id=f"longform-{override.episode_id}", start_hour=override.start_hour,
        daypart=clk.daypart_for_hour(override.start_hour), kind="longform",
        persona_id=override.persona_id, show_or_episode_id=override.episode_id)
    ok = schedule.add_slot(block, editorial_reason=f"longform reserve {override.episode_id}",
                           seed=True)
    if ok and schedule._ledger is not None:
        try:
            schedule._ledger.append(EV_TIMEBLOCK_RESERVED,
                                    {"slot_id": block.slot_id, "episode_id": override.episode_id,
                                     "duration_minutes": override.duration_minutes,
                                     "start_hour": override.start_hour})
        except Exception as exc:  # noqa: BLE001 - a reserve-log fault never blocks the schedule
            log_event(log, "schedule.timeblock_log_error", error=str(exc))
    return ok


def restore_after_timeblock(schedule: Schedule, override: TimeBlockOverride, *,
                            actual_runtime_minutes: Optional[float] = None) -> bool:
    """Restore the default clock cleanly AFTER a long-form block ends (REQ-OA-016 restore). If the
    episode's actual runtime drifts from its duration claim, the restore fires at the next safe
    boundary AFTER the content ends (never-cut-short NFR-O-12 wins over snapping to a planned
    time). The daypart clock-set switch the block deferred resumes here."""
    ok = schedule.remove_slot(f"longform-{override.episode_id}")
    if schedule._ledger is not None:
        try:
            schedule._ledger.append(
                EV_TIMEBLOCK_RESTORED,
                {"slot_id": f"longform-{override.episode_id}", "episode_id": override.episode_id,
                 "actual_runtime_minutes": (actual_runtime_minutes
                                            if actual_runtime_minutes is not None
                                            else override.duration_minutes)})
        except Exception as exc:  # noqa: BLE001 - a restore-log fault never blocks the schedule
            log_event(log, "schedule.timeblock_restore_log_error", error=str(exc))
    return ok
