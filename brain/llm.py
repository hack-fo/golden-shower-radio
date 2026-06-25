"""Claude curation via the MAX subscription (no API key).

Uses the official ``claude-agent-sdk`` (PyPI), which shells out to the bundled
``claude`` CLI. The CLI authenticates via the host's ``~/.claude`` OAuth creds
(mounted at /root/.claude). We must keep two things true:

1. ANTHROPIC_API_KEY MUST be absent from the CLI subprocess env. If present, the
   CLI bills pay-per-use credits and the call FAILS - the exact bug that broke the
   old brain. We strip it from the env we hand to the SDK.

2. We must NOT drag Claude Code's own ~85k-token system prompt + coding tools into
   every call (it burns the 5-hour subscription quota). We achieve this with a
   MINIMAL config:
       - ``system_prompt=<plain string>``  -> a plain string is a fully CUSTOM
         prompt. The heavy Claude Code preset only loads with
         ``{"type": "preset", "preset": "claude_code"}`` - which we never use.
       - ``setting_sources=[]``            -> do NOT load CLAUDE.md / project
         settings / MCP servers / hooks from the filesystem.
       - ``allowed_tools=[]``              -> no tools available.
       - ``max_turns=1``                   -> single response, no agentic loop.
       - ``model=<env ANTHROPIC_MODEL>``   -> default claude-sonnet-4-6.

On ANY SDK error / quota / rate-limit / parse failure we fall back to a built-in
seed list so the station keeps running. This module never raises to its caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from . import ear_writing as _ear_writing
from .logging_setup import log_event

log = logging.getLogger("brain.llm")

# --- The radio-curator persona. Short on purpose (it ships in every call). ---
# Full creative autonomy; tasteful, human, eclectic; NOT corporate/engagement-chasing.
PERSONA = (
    "You are the program director and curator of an autonomous internet radio "
    "station. You are a thoughtful, human-spirited music head with deep, eclectic "
    "taste across eras and genres - the kind of curator who runs a beloved "
    "freeform/college-radio show, not a corporate playlist algorithm. You despise "
    "engagement-chasing, ads, and lowest-common-denominator picks. You have complete "
    "creative freedom over what gets played. When asked for tracks, you respond with "
    "ONLY a JSON array of real, existing songs - no commentary, no markdown fences."
)


# --- Built-in fallback: ~30 real, well-known tracks across genres. ---
# Keeps the station alive when the LLM is unreachable / quota-limited.
SEED_TRACKS: List[Dict[str, str]] = [
    {"artist": "Fleetwood Mac", "title": "Dreams"},
    {"artist": "Marvin Gaye", "title": "What's Going On"},
    {"artist": "Radiohead", "title": "Weird Fishes/Arpeggi"},
    {"artist": "Kendrick Lamar", "title": "Money Trees"},
    {"artist": "Daft Punk", "title": "Something About Us"},
    {"artist": "Nina Simone", "title": "Feeling Good"},
    {"artist": "The Velvet Underground", "title": "Sunday Morning"},
    {"artist": "Aphex Twin", "title": "Avril 14th"},
    {"artist": "Bob Marley & The Wailers", "title": "Could You Be Loved"},
    {"artist": "Talking Heads", "title": "This Must Be the Place"},
    {"artist": "A Tribe Called Quest", "title": "Can I Kick It?"},
    {"artist": "Miles Davis", "title": "So What"},
    {"artist": "Stevie Wonder", "title": "As"},
    {"artist": "Portishead", "title": "Glory Box"},
    {"artist": "The Beatles", "title": "Come Together"},
    {"artist": "Burial", "title": "Archangel"},
    {"artist": "D'Angelo", "title": "Untitled (How Does It Feel)"},
    {"artist": "Joni Mitchell", "title": "A Case of You"},
    {"artist": "LCD Soundsystem", "title": "All My Friends"},
    {"artist": "Curtis Mayfield", "title": "Move On Up"},
    {"artist": "Massive Attack", "title": "Teardrop"},
    {"artist": "Outkast", "title": "Ms. Jackson"},
    {"artist": "Pixies", "title": "Where Is My Mind?"},
    {"artist": "J Dilla", "title": "Don't Cry"},
    {"artist": "Caribou", "title": "Can't Do Without You"},
    {"artist": "Sade", "title": "Cherish the Day"},
    {"artist": "Tame Impala", "title": "Let It Happen"},
    {"artist": "Erykah Badu", "title": "On & On"},
    {"artist": "John Coltrane", "title": "Naima"},
    {"artist": "Frank Ocean", "title": "Nights"},
    {"artist": "Khruangbin", "title": "Maria Tambien"},
    {"artist": "Vulfpeck", "title": "Dean Town"},
]


def _build_options(model: str, system_prompt: str = PERSONA):
    """Construct the minimal ClaudeAgentOptions. Imported lazily so a missing SDK
    only matters at call time (we still fall back to the seed list).

    ``system_prompt`` selects the persona: the curator PERSONA for track picking, or
    HOST_PERSONA for spoken talk links. It MUST stay a plain string (a custom prompt)
    so the heavy claude_code preset never loads - see the ANCHOR below."""
    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    auth_mode = os.environ.get("BRAIN_LLM_AUTH", "oauth")

    if auth_mode == "api_key":
        # Pay-per-use: pass ANTHROPIC_API_KEY through to the subprocess unchanged.
        child_env = dict(os.environ)
    else:
        # "oauth" or "token": strip ANTHROPIC_API_KEY so the CLI uses subscription
        # credentials. In "token" mode CLAUDE_CODE_OAUTH_TOKEN is already in env;
        # the CLI picks it up automatically. Keep HOME so the SDK finds /root/.claude.
        child_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    child_env.setdefault("HOME", "/root")

    # @MX:ANCHOR: [AUTO] minimal Claude config - the subscription-quota + auth contract
    # @MX:REASON: every LLM call ships this config; a wrong field here either bloats
    #   each call with the ~85k-token claude_code preset (burns the 5h quota) or bills
    #   pay-per-use credits (breaks the subscription). Do NOT add permission_mode here:
    #   "bypassPermissions" maps to --dangerously-skip-permissions, which the CLI
    #   REFUSES under root (the container runs as root for /root/.claude). With
    #   allowed_tools=[] there are no tools to prompt for, so default mode is correct.
    return ClaudeAgentOptions(
        system_prompt=system_prompt,  # plain string => custom prompt, NO claude_code preset
        allowed_tools=[],             # no tools (=> nothing to prompt for => no perm mode needed)
        setting_sources=[],           # do not load CLAUDE.md / settings / MCP / hooks
        max_turns=1,                  # one response only
        model=model,                  # from env ANTHROPIC_MODEL (default sonnet)
        env=child_env,                # ANTHROPIC_API_KEY stripped unless BRAIN_LLM_AUTH=api_key
    )


async def _query_text(prompt: str, model: str, system_prompt: str = PERSONA,
                      caller: str = "unknown") -> str:
    """Run a single one-shot query and concatenate the assistant text blocks.

    ``system_prompt`` chooses the persona (curator vs on-air host). ``caller`` tags the
    ADMIN-041 usage record so the admin panel can attribute cost per call site."""
    from claude_agent_sdk import query, AssistantMessage, TextBlock  # type: ignore

    options = _build_options(model, system_prompt=system_prompt)
    chunks: List[str] = []
    last_usage: dict = {}
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            if getattr(message, "usage", None) and isinstance(message.usage, dict):
                last_usage = message.usage
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    result = "".join(chunks)
    _record_usage(caller, prompt, result, last_usage)
    return result


def _extract_tracks(text: str) -> List[Dict[str, str]]:
    """Defensively pull a list of {artist, title} out of arbitrary model text.

    Strategy, in order:
      1. Parse the first ``[ ... ]`` JSON array we can find.
      2. Fall back to line-by-line ``Artist - Title`` parsing.
    Returns [] if nothing usable was found (caller then uses the seed list).
    """
    if not text:
        return []

    # 1) JSON array anywhere in the text (handles ```json fences, prose, etc.).
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            tracks = _coerce_track_list(data)
            if tracks:
                return tracks
        except (json.JSONDecodeError, ValueError):
            pass

    # 2) Line-by-line "Artist - Title".
    tracks: List[Dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*0123456789.) ").strip()
        # Accept en-dash and hyphen separators.
        m = re.match(r"^(.+?)\s+[\-–—]\s+(.+)$", line)
        if m:
            artist = m.group(1).strip().strip('"').strip()
            title = m.group(2).strip().strip('"').strip()
            if artist and title:
                tracks.append({"artist": artist, "title": title})
    return tracks


def _coerce_track_list(data) -> List[Dict[str, str]]:
    tracks: List[Dict[str, str]] = []
    if not isinstance(data, list):
        return tracks
    for item in data:
        if isinstance(item, dict):
            artist = str(item.get("artist") or item.get("Artist") or "").strip()
            title = str(item.get("title") or item.get("Title") or item.get("track") or "").strip()
            if artist and title:
                tracks.append({"artist": artist, "title": title})
        elif isinstance(item, str):
            m = re.match(r"^(.+?)\s+[\-–—]\s+(.+)$", item.strip())
            if m:
                tracks.append({"artist": m.group(1).strip(), "title": m.group(2).strip()})
    return tracks


def _build_prompt(batch_size: int, recent: List[str], seed_reference: List[str],
                  already_have: Optional[List[str]] = None,
                  recently_rejected: Optional[List[str]] = None) -> str:
    parts = [
        f"Give me {batch_size} tracks to play next on the station right now.",
        "Mix it up across genres, eras, and moods - build a great, surprising radio flow.",
        'Respond with ONLY a JSON array of objects: [{"artist": "...", "title": "..."}].',
    ]
    if recent:
        parts.append("Recently played (avoid repeating these): " + "; ".join(recent[:20]) + ".")
    if seed_reference:
        # Non-binding reference: "what the listener considers good music". NOT a constraint.
        parts.append(
            "For loose reference only (the listener's taste - feel free to expand on or "
            "ignore it): " + "; ".join(seed_reference[:15]) + "."
        )
    # PROGRAMMING-007 Group PL (REQ-PL-009) exclusion-feedback: the PERSISTENT acquisition
    # history, ADDITIVE to the EPHEMERAL playout `recent` window (the two-no-repeat separation).
    # `already_have` = recently-acquired catalog members; `recently_rejected` = recently
    # failed / no-candidate items. Feeding these makes the batch propose genuinely NEW
    # candidates the acquisition gate can actually act on, instead of re-proposing items it
    # silently drops (the verified wasted-quota gap). BOTH default empty => no lines added =>
    # the prompt is BYTE-IDENTICAL to before this SPEC (the behaviour-preservation pin).
    if already_have:
        parts.append(
            "Already in the library (do NOT propose these - we already have them): "
            + "; ".join(already_have[:40]) + "."
        )
    if recently_rejected:
        parts.append(
            "Recently tried but could NOT acquire (do NOT propose these again - no source / "
            "failed): " + "; ".join(recently_rejected[:40]) + "."
        )
    return "\n".join(parts)


def _persona_curation_overlay(persona) -> tuple:
    """Build the (system_prompt, extra_prompt_lines) that bias curation toward an ACTIVE
    persona's taste charter (SPEC-RADIO-PROGRAMMING-007 Group PR, REQ-PR-006/PR-014).

    Returns ``(PERSONA, [])`` (the byte-identical house default) when ``persona`` is None or
    carries no usable charter, so the single-default-persona path is unchanged. When an active
    persona is supplied, the curator prompt is specialized to its charter (primary territory,
    in/out genres, eras, moods, signature artists) so it draws a DISTINCT candidate pool —
    while still inheriting the house ethos."""
    if persona is None:
        return PERSONA, []
    ch = getattr(persona, "charter", None)
    name = str(getattr(persona, "display_name", "") or "").strip()
    primary = str(getattr(ch, "primary_territory", "") or "").strip() if ch else ""
    if not name and not primary:
        return PERSONA, []
    sys_prompt = (
        PERSONA + " For this show you ARE the curator-persona "
        f"\"{name}\"" + (f", whose primary territory is {primary}." if primary else ".") +
        " Pick tracks that fit THIS persona's distinct taste, not a generic average."
    )
    lines: List[str] = []
    if ch is not None:
        in_g = ", ".join([g for g in (getattr(ch, "in_genres", []) or [])][:8])
        out_g = ", ".join([g for g in (getattr(ch, "out_genres", []) or [])][:8])
        eras = ", ".join([e for e in (getattr(ch, "in_eras", []) or [])][:6])
        moods = ", ".join([m for m in (getattr(ch, "moods", []) or [])][:6])
        arts = ", ".join([a for a in (getattr(ch, "signature_artists", []) or [])][:8])
        if primary:
            lines.append(f"Your primary territory (lead with it): {primary}.")
        if in_g:
            lines.append(f"In-bounds genres: {in_g}.")
        if out_g:
            lines.append(f"Out-of-bounds (avoid): {out_g}.")
        if eras:
            lines.append(f"Favoured eras: {eras}.")
        if moods:
            lines.append(f"Moods: {moods}.")
        if arts:
            lines.append(f"Signature artists/labels to echo (not copy): {arts}.")
    return sys_prompt, lines


def curate_batch(
    model: str,
    batch_size: int = 25,
    recent: Optional[List[str]] = None,
    seed_reference: Optional[List[str]] = None,
    persona=None,
    already_have: Optional[List[str]] = None,
    recently_rejected: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Return a batch of {artist, title} dicts. NEVER raises; always returns >=1.

    On any SDK error / quota / rate-limit / empty parse, falls back to the built-in
    seed list (shuffled) so the station keeps running.

    ``persona`` (SPEC-RADIO-PROGRAMMING-007 Group PR) is OPTIONAL and DEFAULTS to None. When
    None the curation is BYTE-IDENTICAL to before this SPEC (the house curator PERSONA). When
    an active persona is supplied (opt-in multi-persona), curation is biased toward its taste
    charter so it draws a distinct candidate pool (REQ-PR-014).

    ``already_have`` / ``recently_rejected`` (Group PL, REQ-PL-009) are the OPTIONAL persistent-
    acquisition exclusion sets, ADDITIVE to the ephemeral playout ``recent`` (the two-no-repeat
    separation). BOTH default empty => the prompt is byte-identical to before this SPEC.
    """
    recent = recent or []
    seed_reference = seed_reference or []
    prompt = _build_prompt(batch_size, recent, seed_reference, already_have, recently_rejected)
    system_prompt, persona_lines = _persona_curation_overlay(persona)
    if persona_lines:
        prompt = prompt + "\n" + "\n".join(persona_lines)

    try:
        text = asyncio.run(_query_text(prompt, model, system_prompt=system_prompt, caller="curate"))
        tracks = _extract_tracks(text)
        if tracks:
            log_event(log, "llm.curated", count=len(tracks), model=model)
            return tracks
        log_event(log, "llm.empty_parse", model=model, raw_len=len(text or ""))
    except Exception as exc:  # noqa: BLE001 - resilience is the whole point
        log_event(log, "llm.error_fallback_to_seed", error=str(exc), model=model)

    # Fallback: shuffle a copy of the seed list so we don't always start identically.
    import random

    seed = list(SEED_TRACKS)
    random.shuffle(seed)
    return seed[: max(batch_size, 1)]


# =====================================================================================
# TALKING layer (phase 2a): host talk-script generation.
#
# The on-air persona writes a SHORT spoken link between songs - a back-announce of the
# track that just played and/or an intro to the one coming up. This reuses the SAME
# minimal-config _query_text() path as curation (tools-off, subscription auth, one turn)
# so it stays cheap on the 5-hour quota. On ANY error we return "" and the caller skips
# the talk break (music never blocks on the DJ).
#
# This is the cheap "Mode A" link generation. Deeper researched banter (Mode B: web
# lookups, artist trivia, multi-host dialogue) is a later phase and would extend this
# with extra context fields / a richer prompt - the signature already takes a context
# dict so that lands without reshaping callers.
# =====================================================================================

# A distinct persona for the SPOKEN voice. The curator picks tracks; the HOST talks on
# air. Kept short (ships in every talk call) and explicitly anti-AI-slop.
HOST_PERSONA = (
    "You are the live on-air host (DJ) of an autonomous freeform internet radio "
    "station. You speak in a natural, warm, slightly witty radio-host voice - the "
    "voice of a real human who loves this music, not a corporate announcer and not a "
    "chirpy AI assistant. You riff briefly, with taste and personality. Your spoken "
    "links are SHORT (one to three sentences), easy to say out loud, and never use "
    "stage directions, emojis, markdown, or quotation marks - just the words you would "
    "actually say into the mic."
)


# =====================================================================================
# Group PV (SPEC-RADIO-PROGRAMMING-007 Section 9c): host-voice persona-awareness +
# delivery craft. ALL of the following PV prompt enrichment is GATED behind the context
# key ``pv_voice`` (set by talk.py only when cfg.host_voice_pv_enabled is ON). With the
# key ABSENT (the default), _build_talk_prompt + the host system prompt are BYTE-IDENTICAL
# to the pre-PV form, EXCEPT the REQ-PV-008 frontsell code-fix which is UNCONDITIONAL (the
# "Coming up next" name block was a currently-airing banned-phrase regression).
# =====================================================================================

# REQ-PV-001 / REQ-PV-015 — the POSITIVE-IDENTITY host persona that REPLACES the negation-
# based HOST_PERSONA ("not a corporate announcer / not a chirpy AI"). A concrete music-
# journalist register lineage + a one-to-one addressee frame steers the model off the
# flowery-press-release default. A DELIVERY stance ONLY — the host never SAYS it is a
# journalist, never claims to be live/real/an AI/a script, never breaks the fourth wall.
# Grounding (REQ-PG-002) is UNTOUCHED: self-awareness adds warmth, not claim-making latitude.
POSITIVE_HOST_PERSONA = (
    "You are a live human radio host — one person, one microphone, talking to one listener. "
    "You sound like a BBC 6 Music / NTS / KEXP presenter: a working music head who genuinely "
    "loves this stuff, knowledgeable, dry, and funny, who says plainly when something rules and "
    "plainly when it doesn't. Talk like you're texting one smart, slightly-impatient friend "
    "about this song — present tense, second person, warmth carried in rhythm and timing. Never "
    "say you are live, real, an AI, a script, or a journalist, and never break the fourth wall. "
    "Speak ONLY from verified facts; being a real human adds warmth of delivery, not new claims. "
    "Your spoken links are short, easy to say out loud, and use no stage directions, emojis, "
    "markdown, or quotation marks — just the words you would say into the mic."
)

# REQ-PV-006 — the ban -> positive "say this instead" TWIN pairings carried IN the prompt to
# fill the vacuum the bans leave (the diagnosed pink-elephant retreat). The bans stay the
# Tier-1 firewall (enforced in grounding.py); the twins steer FORM only — the fact contract
# still supplies all CONTENT. TUNABLE wording; that twins are carried is the rail.
_BAN_TWINS = (
    "When you'd reach for \"transports you\", say what the song actually does to you in plain "
    "words.",
    "When you'd reach for \"an infectious banger\", just say it goes, or it rules, or it kicks.",
    "When you'd reach for \"a sonic journey\", name one thing you can actually hear.",
    "Never say \"coming up\", \"up next\", \"stay tuned\", or \"don't go anywhere\".",
)

# REQ-PV-015 — 2-4 ROTATED GOOD-vs-BAD exemplar pairs using GENERIC/placeholder tracks (never
# the real upcoming track), labelled "the VOICE to hit, NOT lines to reuse". HAND-AUTHORED
# anchors (no-self-imitation REQ-OC-006 holds — never fed-back station scripts). TUNABLE set.
_VOICE_EXEMPLARS = (
    ("a captivating sonic journey that effortlessly transports you",
     "that synth line just will not sit still — love it"),
    ("an anthemic, infectious banger for all your favourites",
     "this one rules; the drums do not let up once"),
    ("a lush, hypnotic soundscape that needs no introduction",
     "play this loud — the bass is the whole point"),
    ("a timeless masterpiece, truly a testament to the era",
     "still sounds enormous; that chorus earns it"),
)

# REQ-PV-002 / REQ-PV-004 — the ear-writing rails + the calibrated delivery DO-set carried IN
# the live prompt. The rails text is OWNED by Group PS (brain.ear_writing) — the SINGLE SOURCE
# OF TRUTH; PV reads it from there (the inline fork is eliminated, the same single-source pattern
# as the PC daypart presets and the PI anchor block). The blank-line block instruction is the
# REQ-PS-004 coordination contract (VOICE-002 chunks at the blank lines) — present, not broken.
_EAR_WRITING_RAILS = _ear_writing.ear_writing_rails()


def _craft_prompt_blocks(context: Dict) -> List[str]:
    """The Group PC radio-craft prompt blocks (REQ-PC-001/007/009/010).

    Carried in the live prompt ONLY when context["craft"] is set. Composes:
      * the talk-break ANATOMY (REQ-PC-001) — Hook -> Body -> Exit, BACKSELL default, FRONTSELL
        by feeling (never the banned filler), plus this break's ROTATED say-category (REQ-PC-007,
        from context["say_category"]) and the periodic in-link RE-ID (REQ-PC-009, when
        context["reid"] is set);
      * for an OPENING (context["welcome"]/["opening"]), the open-on-the-strongest-hook rule
        (REQ-PC-010).
    The rules are PC-owned editorial knowledge (REQ-PC-008); the copy stays AI-authored. Drawn
    from the single-source playbook (no fork)."""
    from . import playbook
    blocks: List[str] = []
    if context.get("opening") or context.get("welcome"):
        blocks.extend(playbook.open_strongest_block())
    blocks.extend(playbook.talk_anatomy_blocks(
        say_category=str(context.get("say_category") or "").strip(),
        include_reid=bool(context.get("reid")),
        station_name=str(context.get("station_name") or "").strip(),
    ))
    return blocks


def _pv_prompt_blocks(context: Dict, persona=None) -> List[str]:
    """The Group PV delivery-craft prompt blocks (REQ-PV-002/004/005/006/009/015/019).

    Carried in the live prompt ONLY when context["pv_voice"] is set. Composes:
      * the extended per-persona VOICE CARD (REQ-PV-009) via grounding.pv_voice_card_for,
        including the per-daypart energy band (REQ-PV-003);
      * the warmth-in-delivery / restraint-in-content spine (REQ-PV-005);
      * the ear-writing rails + the calibrated delivery DO-set (REQ-PV-002/004);
      * the ban -> positive-twin pairings (REQ-PV-006) + form-not-content exemplars (REQ-PV-015);
      * the long-form ARC-PHASE, when threading a multi-segment episode (REQ-PV-019).
    Drawn from authored fields + hand-authored anchors only (no-self-imitation REQ-OC-006)."""
    from . import grounding
    blocks: List[str] = []
    daypart = str(context.get("daypart") or "").strip()
    # The extended voice card (REQ-PV-009) — delivery shape + opinion-about-the-audible only,
    # never a fact. Composes the PG-006 base card with the PV energy band / pacing / register /
    # disjoint tic bank.
    blocks.append(grounding.pv_voice_card_for(persona, daypart))
    # REQ-PV-005 — the governing spine.
    blocks.append(
        "Warmth and energy in DELIVERY; restraint in CONTENT. Turn the warmth, energy, "
        "bluntness and humour up — but state no fact you cannot point to, pile no adjectives, "
        "and never reach for hype. Energy is a writing property, not exclamation marks."
    )
    # REQ-PV-002 / REQ-PV-004 — the ear-writing rails + the DO-set.
    blocks.extend(_EAR_WRITING_RAILS)
    # REQ-PV-006 — the ban -> positive twin pairings.
    blocks.append("Say it like a person, not a press release:")
    blocks.extend(f"- {t}" for t in _BAN_TWINS)
    # REQ-PV-015 — 2-4 form-not-content exemplars (rotated by a stable per-persona offset so a
    # given persona sees a consistent subset; generic placeholder tracks, never the real one).
    exemplars = _rotated_exemplars(persona)
    if exemplars:
        blocks.append("These show the VOICE to hit, NOT lines to reuse:")
        for bad, good in exemplars:
            blocks.append(f"- not \"{bad}\" — rather \"{good}\"")
    # REQ-PV-019 — long-form arc-phase (when present): inject the current beat so per-segment
    # delivery is phase-aware WITHOUT changing WHO the persona is (the frozen anchor is carried
    # by the voice card above). The arc-phase taxonomy is the conceived format's (referenced).
    arc_phase = str(context.get("arc_phase") or "").strip()
    if arc_phase:
        blocks.append(
            f"This is the \"{arc_phase}\" beat of a longer episode. Let the delivery reflect "
            "that beat (an open reads differently from a reflective close) while staying the "
            "exact same person — same temperament, same voice signature, start to finish."
        )
    return blocks


def _rotated_exemplars(persona, count: int = 2):
    """Pick a stable subset of ``count`` GOOD-vs-BAD exemplar pairs (REQ-PV-015). The offset is
    derived deterministically from the persona id so a given persona sees a consistent rotation
    (and the unhosted/house path a fixed default), per the "rotated, hand-authored anchors" rail."""
    if not _VOICE_EXEMPLARS:
        return []
    n = len(_VOICE_EXEMPLARS)
    pid = str(getattr(persona, "id", "") or "") if persona is not None else ""
    off = (sum(ord(c) for c in pid) % n) if pid else 0
    return [_VOICE_EXEMPLARS[(off + i) % n] for i in range(min(count, n))]


def _build_talk_prompt(context: Dict, persona=None) -> str:
    """Turn a talk context dict into a single one-shot prompt for the host persona.

    Recognised keys (all optional):
      last_artist / last_title  - the track that just finished (for a back-announce)
      next_mood                 - SPEC-RADIO-PROGRAMMING-007 REQ-PV-007/008: a MOOD/energy
                                  hint for the NEXT track (NEVER its name) for a tease-by-
                                  feeling frontsell. The next track's artist/title NAME is
                                  NEVER passed for a between-song break (the name is reserved
                                  for the FOLLOWING break's backsell, REQ-PC-001).
      next_artist / next_title  - the WELCOME path's FIRST song (opening intro only; a
                                  between-song break never carries the next track's name).
      pv_voice                  - REQ-PV: when truthy, inject the Group PV delivery-craft
                                  enrichment (positive register, ear-writing rails, ban-twins,
                                  exemplars, the extended voice card, daypart energy band, the
                                  long-form arc-phase). Absent => byte-identical pre-PV prompt.
      daypart                   - REQ-PV-003: the current daypart name (for the energy band).
      arc_phase                 - REQ-PV-019: the long-form episode's current arc beat (injected
                                  into the per-segment voice-card call so delivery is phase-aware).
      station_name              - station identity, for the occasional ident
      last_year / last_album    - SPEC-RADIO-HOSTCTX-016 (Group HY): the VERIFIED release
                                  year + album of the JUST-PLAYED track (read from the
                                  ANALYSIS-006 Track record, filled by ENRICH-012). Backsell
                                  detail only; the host MAY (not must) voice them, quoted
                                  exactly. Absent/empty => simply not offered (graceful
                                  omission). NEVER read for the next track (REQ-PV-007/008).
      grounded_facts            - KNOWLEDGE-008 verified facts (REQ-KI-001): a list of
                                  {predicate, value, certain, hedge, ...}. CERTAIN facts may
                                  be stated plainly; QUALIFIED facts MUST carry their hedge.
                                  HOSTCTX-016 (Group HC): one of these MAY be voiced as a
                                  short grounded curiosa about the just-played track.
      grounded_relations        - KNOWLEDGE-008 real graph edges (REQ-KG-004): a list of
                                  {rel, target, ...} the host may segue on (real edges only).

    ``persona`` (SPEC-RADIO-PROGRAMMING-007 Group PR) is OPTIONAL and DEFAULTS to None. It
    threads the ACTIVE persona's authored voice surface (POV + taste charter) and a stable
    per-persona CADENCE-LEAN into the HOSTCTX-016 year/album/curiosa block so each host's
    delivery of those facts is OBSERVABLY DISTINGUISHABLE (REQ-HD-002 / NFR-H-3) — one host
    digs into release history, another barely mentions years. [HARD] With ``persona`` None
    (the default / unhosted house path) the prompt is BYTE-IDENTICAL to before this wiring,
    and the unhosted DIRECTOR-DISCRETION framing (REQ-HD-003) is expressed instead. The
    persona flavour is confined to the year/album/curiosa block — it never invents a fact and
    never relaxes the grounding rule.
    """
    last_artist = str(context.get("last_artist") or "").strip()
    last_title = str(context.get("last_title") or "").strip()
    next_artist = str(context.get("next_artist") or "").strip()
    next_title = str(context.get("next_title") or "").strip()
    station = str(context.get("station_name") or "").strip()

    # First-run WELCOME: a one-shot opening, longer than a normal between-song link. The
    # listener has just tuned in to a station that just came on air, so there is nothing to
    # back-announce — open the broadcast, say who you are, explain briefly how it works, then
    # hand into the first song. The explicit length here overrides the persona's "short link"
    # default for this single segment.
    if context.get("welcome"):
        wparts: List[str] = [
            "This is the station's OPENING WELCOME — the very first thing listeners hear as "
            "the station comes on air, NOT a between-song link.",
            "Speak for about 30 to 60 seconds (roughly 90 to 150 words). Natural spoken "
            "English, warm and inviting. Output ONLY the words to say — no quotes, no "
            "markdown, no stage directions, no song metadata formatting.",
            "Cover, in your own voice and in this order: (1) welcome the listener and name "
            "the station" + (f" ({station})" if station else "") + "; (2) say who you are — "
            "the live on-air host; (3) explain briefly how this works: it's an autonomous "
            "station that finds and plays music around the clock and you pop in between songs "
            "to talk; (4) then introduce the first song.",
        ]
        if next_artist or next_title:
            wparts.append(f"The first song is: \"{next_title}\" by {next_artist}." if next_artist
                          else f"The first song is: \"{next_title}\".")
            wparts.append("Hand into it naturally — name the artist and title so listeners "
                          "know what they're about to hear.")
        else:
            wparts.append("Then hand into the music without naming a specific track.")
        wparts.append("Keep it genuine and easy to say out loud — an opening, not a sales pitch.")
        return "\n".join(wparts)

    parts: List[str] = [
        "Write a SHORT spoken radio link to say between songs, right now, live on air.",
        "One to three sentences. Natural spoken English. Output ONLY the words to say - "
        "no quotes, no markdown, no stage directions, no song metadata formatting.",
    ]
    # SPEC-RADIO-PROGRAMMING-007 Group PV — GATED delivery-craft enrichment (REQ-PV-002/004/
    # 005/006/009/015/019). Injected ONLY when context["pv_voice"] is truthy (talk.py sets it
    # when cfg.host_voice_pv_enabled). Absent => byte-identical pre-PV prompt. The enrichment
    # carries the extended voice card, the ear-writing rails, the warmth/restraint spine, the
    # ban->positive-twin pairings, the form-not-content exemplars, and the long-form arc-phase.
    if context.get("pv_voice"):
        parts.extend(_pv_prompt_blocks(context, persona))
    # SPEC-RADIO-PROGRAMMING-007 Group PC — GATED radio-craft enrichment (REQ-PC-001/007/009/010).
    # Injected ONLY when context["craft"] is set (talk.py sets it when cfg.craft_playbook_enabled).
    # Absent => byte-identical pre-PC prompt. Carries the talk-break ANATOMY (Hook->Body->Exit +
    # backsell-default + frontsell-by-feeling), this break's ROTATED say-category, the periodic
    # in-link RE-ID, and (for an opening) the open-on-the-strongest-hook rule.
    if context.get("craft"):
        parts.extend(_craft_prompt_blocks(context))
    if last_artist or last_title:
        parts.append(f"You just played: \"{last_title}\" by {last_artist}." if last_artist
                     else f"You just played: \"{last_title}\".")
        parts.append("Briefly back-announce it (a touch of character or a tasteful aside is welcome).")
        # SPEC-RADIO-HOSTCTX-016 Group HY (REQ-HY-001/002/003): offer the VERIFIED release
        # year + album of the just-played track as an OPTIONAL backsell detail the host MAY
        # use. Quoted EXACTLY so the gate's forbidden-fact scan finds every token in context;
        # framed as a cycled option (not an every-break template, REQ-HD-001 / R-H-3), and
        # only rendered when the value is actually present (graceful omission, REQ-HY-001/002).
        # The per-persona LEAN / unhosted DIRECTOR-DISCRETION line (REQ-HD-002/003) rides INSIDE
        # this block, so a bare backsell with no year/album stays byte-identical.
        year_album = _format_year_album(context.get("last_year"), context.get("last_album"))
        if year_album:
            parts.extend(year_album)
            parts.append(_year_album_cadence_line(persona))
    # SPEC-RADIO-PROGRAMMING-007 REQ-PV-007/008 — TEASE-BY-FEELING FRONTSELL (the mandatory
    # code-fix). The OLD code emitted `Coming up next: "{title}" by {artist}.` + "name the
    # artist and title" — a currently-airing banned-phrase regression (REQ-PC-004/REQ-PV-006)
    # that named the upcoming track. It is REMOVED unconditionally. The next track is now
    # supplied as a MOOD hint only (``next_mood``, derived from ANALYSIS-006 features), never a
    # name; the host MAY tease ONLY its feeling/energy shift and MUST NOT name it or use the
    # banned filler. The artist+title NAME is reserved for the FOLLOWING break's backsell.
    next_mood = str(context.get("next_mood") or "").strip()
    if next_mood:
        parts.append(
            f"The next track feels: {next_mood}. You MAY tease ONLY that shift in mood or "
            "energy (\"the next one sits lower, slower\") — do NOT name the artist or title, "
            "and do NOT say \"coming up\", \"up next\", or \"stay tuned\"."
        )
    if station:
        parts.append(f"You may occasionally (not every time) drop the station name: {station}.")

    # KNOWLEDGE-008 grounding (REQ-KI-001): the host speaks ONLY from these verified, dated
    # facts — never free-recalled biography. Additive + backward-compatible: with no grounded
    # facts the prompt is byte-identical to the pre-SPEC form. CERTAIN facts may be stated as
    # established; QUALIFIED facts MUST be voiced with their hedge ("reportedly", "according
    # to ...") and never as established (REQ-KS-006). Relations are real graph edges the host
    # may segue on; the host MUST NOT invent a relationship not listed here (REQ-KG-004).
    grounded_lines = _format_grounding(context.get("grounded_facts"),
                                       context.get("grounded_relations"))
    if grounded_lines:
        parts.append(
            "Verified facts you MAY use (speak ONLY from these — do not invent or recall any "
            "other facts about the artist):"
        )
        parts.extend(grounded_lines)
        parts.append(
            "State CERTAIN facts plainly; for any fact marked QUALIFIED you MUST keep its "
            "hedge and never present it as established. Only segue on a listed relationship."
        )
        # SPEC-RADIO-HOSTCTX-016 Group HC (REQ-HC-001/002/003): the host MAY turn ONE of the
        # supplied facts above into a short curiosa / anecdote about the just-played track —
        # but ONLY from those supplied, sourced facts (the single KNOWLEDGE-008 feed seam,
        # REQ-HW-003). A curiosa it cannot point to in the facts above is FORBIDDEN exactly
        # like an unsourced claim (grounding REQ-PG-002); never invent one to fill the slot.
        parts.append(
            "You MAY (not every break) work ONE of these into a short, genuinely interesting "
            "curiosa or anecdote about the track — at most one, kept brief — drawn ONLY from "
            "the facts above; do not invent or imply any anecdote not listed here."
        )
        # SPEC-RADIO-HOSTCTX-016 REQ-HD-002/003: colour the curiosa in the ACTIVE persona's own
        # voice (or, unhosted, leave it to the director's discretion) so the curiosa cadence is
        # distinguishable per host — never a uniform every-host anecdote habit (NFR-H-3).
        parts.append(_curiosa_cadence_line(persona))

    # SPEC-RADIO-SHOWS-020 (REQ-SD-002/003): when an active show is presenting, offer its
    # editorial THEME as framing (NOT a fact) + any GROUNDED talking points (the airable ones —
    # the show engine pre-filters; an ungrounded show-design note never reaches here). Additive
    # + backward-compatible: with no active show the keys are absent and the prompt is
    # byte-identical. A talking point is still a fact token subject to the unchanged grounding
    # gate downstream — the show theme licenses no ungrounded claim (REQ-SD-003).
    show_lines = _format_show_context(context.get("show_theme"),
                                      context.get("show_talking_points"))
    if show_lines:
        parts.extend(show_lines)

    parts.append("Keep it tight - this is a link, not a monologue.")
    return "\n".join(parts)


def _format_show_context(theme, talking_points) -> List[str]:
    """Render the active show's theme + grounded talking points into OPTIONAL prompt lines
    (SPEC-RADIO-SHOWS-020 REQ-SD-002/003).

    Returns [] when neither is present so the prompt stays byte-identical (graceful omission).
    The theme is EDITORIAL FRAMING (the kind of show this is), explicitly NOT an airable fact;
    the talking points are grounded notes the host MAY voice — still subject to the unchanged
    forbidden-fact gate downstream. A compelling theme never licenses an ungrounded claim.
    """
    lines: List[str] = []
    theme_text = str(theme or "").strip()
    if theme_text:
        lines.append(
            f"This show's editorial theme (framing for your tone — NOT a fact to assert): "
            f"{theme_text}."
        )
    points = [str(p).strip() for p in (talking_points or []) if str(p).strip()]
    if points:
        lines.append(
            "Grounded show talking points you MAY weave in (speak ONLY from these — they are "
            "already grounded; do not invent any other show fact):"
        )
        lines.extend(f"- {p}" for p in points)
    return lines


def _format_year_album(year, album) -> List[str]:
    """Render the verified release year + album of the just-played track into OPTIONAL
    backsell prompt lines (SPEC-RADIO-HOSTCTX-016 Group HY).

    Returns [] when neither is present so the prompt stays the plain backsell (graceful
    omission, REQ-HY-001/002 — absence is never a defect). Both are quoted EXACTLY: the year
    as its 4-digit value and the album as its verified title, so every spoken token traces to
    the supplied fact contract and passes the unchanged REQ-PG-005 forbidden-fact scan. The
    'may' framing keeps it a cycled option, never a mandatory every-break template (REQ-HD-001).
    """
    # A year is only a fact token when it is a real positive 4-digit-ish value; 0/None/""/
    # a non-numeric tag never renders (no guessed or partial year, REQ-HY-001).
    spoken_year = ""
    try:
        y = int(str(year).strip()) if year not in (None, "") else 0
        if y > 0:
            spoken_year = str(y)
    except (TypeError, ValueError):
        spoken_year = ""
    spoken_album = str(album or "").strip()
    if not spoken_year and not spoken_album:
        return []
    if spoken_year and spoken_album:
        detail = f"released in {spoken_year}, off the album \"{spoken_album}\""
    elif spoken_year:
        detail = f"released in {spoken_year}"
    else:
        detail = f"off the album \"{spoken_album}\""
    return [
        f"Verified backsell detail you MAY mention (quote it exactly, do not approximate): "
        f"that track was {detail}.",
        # SPEC-RADIO-HOSTCTX-016 REQ-HD-001 / AC-HD-001 / B3 [HARD]: cycle the move — do NOT
        # mechanically append it to every break. Vary WHICH of year/album/curiosa you use (or
        # none), HOW you phrase it, and WHEN it appears; over-using it is template fatigue.
        "Treat this as a cycled option, not a fixed template: vary whether and how you mention "
        "the year and album from break to break — never the same mechanical 'from {year}, off "
        "{album}' every time.",
    ]


# Stable per-persona CADENCE LEANS (SPEC-RADIO-HOSTCTX-016 REQ-HD-002 / NFR-H-3). A small,
# fixed set of distinct tendencies for HOW a host treats year/album/curiosa. The lean is
# chosen DETERMINISTICALLY from the persona's identity (its id) so a given persona always
# presents consistently (the persistent-returning-person rail, REQ-PR-005) while DIFFERENT
# personas land on observably different cadences across the roster — "one host leans into
# release-history curiosa, another barely mentions years." This is a tendency nudge, not a
# new fact and not a fabricated taste field; it never relaxes the grounding rule.
_YEAR_ALBUM_LEANS = (
    "You tend to lean INTO release history — you enjoy naming the year and album and what "
    "came of it, when there's something there.",
    "You mention years and albums SPARINGLY — you usually lead with the feel of the track and "
    "only drop a year or album when it genuinely adds something.",
    "You treat the year and album as a light, occasional touch — a quick aside at most, never "
    "the centre of the back-announce.",
)
_CURIOSA_LEANS = (
    "When a grounded fact is interesting, you like to turn it into a little story.",
    "You keep curiosa rare and dry — a single sharp detail, never a ramble.",
    "You mostly let the music speak and only reach for a curiosa when it's genuinely striking.",
)


def _persona_lean_index(persona, n: int) -> int:
    """Deterministically map a persona to one of ``n`` stable leans via its id (REQ-HD-002).

    A persona with no id (or no persona at all) is the house/unhosted default and returns -1
    so the caller emits the director-discretion framing instead of a persona lean."""
    if persona is None:
        return -1
    pid = str(getattr(persona, "id", "") or "").strip()
    if not pid:
        return -1
    return sum(ord(c) for c in pid) % max(1, n)


def _persona_flavor(persona) -> str:
    """A short, persona-authored flavour suffix (POV + primary taste territory) echoed into the
    year/album/curiosa instruction so two distinct personas read observably differently
    (REQ-HD-002). Drawn ONLY from the persona's own authored fields — never fabricated. Returns
    "" for the house/unhosted default (no persona) so that path stays byte-identical."""
    if persona is None:
        return ""
    pov = str(getattr(persona, "pov_seed", "") or "").strip()
    ch = getattr(persona, "charter", None)
    territory = str(getattr(ch, "primary_territory", "") or "").strip() if ch else ""
    bits = []
    if territory:
        bits.append(f"your territory is {territory}")
    if pov:
        bits.append(f"your point of view: {pov}")
    return " (" + "; ".join(bits) + ")" if bits else ""


def _year_album_cadence_line(persona) -> str:
    """The per-persona (or unhosted director-discretion) cadence instruction for year/album
    (SPEC-RADIO-HOSTCTX-016 REQ-HD-002/003). For an active persona it picks that persona's
    stable lean + echoes its authored flavour, so the delivery is distinguishable per host.
    With no persona it expresses the DIRECTOR'S DISCRETION rail — "you're the director" — the
    same grounded/verified rails still apply, only the cadence is the director's call."""
    idx = _persona_lean_index(persona, len(_YEAR_ALBUM_LEANS))
    if idx < 0:
        return (
            "No host is scheduled, so this is the director's discretion: choose for yourself "
            "whether and how to use the year and album on this break — cycling them, never "
            "templating them — while keeping every spoken value exactly as given above."
        )
    return "In your own style: " + _YEAR_ALBUM_LEANS[idx] + _persona_flavor(persona)


def _curiosa_cadence_line(persona) -> str:
    """The per-persona (or unhosted director-discretion) cadence instruction for curiosa
    (SPEC-RADIO-HOSTCTX-016 REQ-HD-002/003). Mirrors ``_year_album_cadence_line`` for the
    optional grounded curiosa so the anecdote habit is distinguishable per host and, unhosted,
    is the director's call — never a uniform every-host behaviour (NFR-H-3)."""
    idx = _persona_lean_index(persona, len(_CURIOSA_LEANS))
    if idx < 0:
        return (
            "No host is scheduled: at the director's discretion decide whether a curiosa fits "
            "this break at all — still only ever from the grounded facts above."
        )
    return "In your own style: " + _CURIOSA_LEANS[idx] + _persona_flavor(persona)


def _format_grounding(facts, relations) -> List[str]:
    """Render KNOWLEDGE-008 grounded facts + relations into prompt bullet lines.

    Returns [] when there is nothing grounded so the prompt stays unchanged (the host then
    falls back to genre/feel talk, Scenario B-6). CERTAIN vs QUALIFIED is made explicit so
    the host never voices an unconfirmed fact as established (REQ-KI-001 / REQ-KS-006).
    """
    lines: List[str] = []
    for f in (facts or []):
        if not isinstance(f, dict):
            continue
        predicate = str(f.get("predicate") or "").strip()
        value = str(f.get("value") or "").strip()
        if not value:
            continue
        label = f"{predicate}: {value}" if predicate else value
        if f.get("certain"):
            lines.append(f"- [CERTAIN] {label}")
        else:
            hedge = str(f.get("hedge") or "reportedly").strip()
            lines.append(f"- [QUALIFIED — say '{hedge}'] {label}")
    for r in (relations or []):
        if not isinstance(r, dict):
            continue
        rel = str(r.get("rel") or "").strip().replace("_", " ")
        target = str(r.get("target") or "").strip()
        if rel and target:
            lines.append(f"- [RELATION] {rel} -> {target}")
    return lines


def _clean_talk_text(text: str) -> str:
    """Strip the markdown / quoting / stage-direction noise a model sometimes adds, so
    the TTS engine speaks clean words. Returns "" if nothing usable remains."""
    if not text:
        return ""
    t = text.strip()
    # Drop code fences the model occasionally wraps around the line.
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t).strip()
    # Remove leftover markdown emphasis and bracketed stage directions like [laughs].
    t = re.sub(r"[*_`#]+", "", t)
    t = re.sub(r"\[[^\]]*\]", "", t)
    # Strip straight/curly quote characters entirely - they're never spoken, and the
    # model sometimes wraps the whole line, or just the song title, in quotes.
    t = re.sub(r"[\"'‘’“”]", "", t)
    # Collapse whitespace/newlines into speakable single spaces.
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _persona_host_prompt(persona, pv_voice: bool = False) -> str:
    """The on-air HOST system prompt, optionally specialized to an ACTIVE persona's POV +
    identity (SPEC-RADIO-PROGRAMMING-007 Group PR, REQ-PR-005/PR-014).

    Returns the byte-identical house HOST_PERSONA when ``persona`` is None or carries no POV
    (and PV is off), so the single-default-persona talk path is unchanged. With an active
    persona the host speaks as that named, persistent person (its POV seed) while keeping the
    house voice rules (short, natural, no slop).

    ``pv_voice`` (SPEC-RADIO-PROGRAMMING-007 REQ-PV-001/015) is OPTIONAL and DEFAULTS to False
    so the system prompt is byte-identical to the pre-PV form. When True the host's base
    identity is the POSITIVE-IDENTITY music-journalist register (``POSITIVE_HOST_PERSONA``)
    that REPLACES the negation-based HOST_PERSONA — the diagnosed wiring fix (REQ-PV-015)."""
    base = POSITIVE_HOST_PERSONA if pv_voice else HOST_PERSONA
    if persona is None:
        return base
    name = str(getattr(persona, "display_name", "") or "").strip()
    pov = str(getattr(persona, "pov_seed", "") or "").strip()
    if not name and not pov:
        return base
    extra = " You are the host persona"
    if name:
        extra += f" \"{name}\""
    extra += "."
    if pov:
        extra += f" Your persistent point of view: {pov}"
    extra += " Stay consistently this same returning person."
    return base + extra


def generate_talk_script(model: str, context: Dict, persona=None) -> str:
    """Generate a SHORT host talk link for the given context. NEVER raises.

    Returns the clean spoken text, or "" on any SDK error / quota / empty parse so the
    caller can skip the talk break and just play the next song. Cheap by design: same
    tools-off, one-turn, subscription-auth config as curation, with a HOST system prompt.

    ``persona`` (SPEC-RADIO-PROGRAMMING-007 Group PR) is OPTIONAL and DEFAULTS to None. When
    None the talk is BYTE-IDENTICAL to before this SPEC (the house HOST_PERSONA). When an
    active persona is supplied the host speaks as that named, persistent person (REQ-PR-014).
    """
    prompt = _build_talk_prompt(context, persona)
    # REQ-PV-001/015: when PV delivery-craft is on (context["pv_voice"]), the host's base
    # system identity becomes the positive music-journalist register. Off => byte-identical.
    system_prompt = _persona_host_prompt(persona, bool(context.get("pv_voice")))
    try:
        text = asyncio.run(_query_text(prompt, model, system_prompt=system_prompt, caller="talk"))
        spoken = _clean_talk_text(text)
        if spoken:
            log_event(log, "llm.talk_script", model=model, chars=len(spoken))
            return spoken
        log_event(log, "llm.talk_empty_parse", model=model, raw_len=len(text or ""))
    except Exception as exc:  # noqa: BLE001 - talk is best-effort; never crash playout
        log_event(log, "llm.talk_error", error=str(exc), model=model)
    return ""


# A tight system prompt for the Tier-2 adversarial self-check (SPEC-RADIO-PROGRAMMING-007
# REQ-PG-005). The model acts as a skeptical fact-checker over its OWN draft: it lists every
# factual claim and outputs ONLY the claims NOT supported by the supplied context. Kept short.
FACTCHECK_PERSONA = (
    "You are a strict radio fact-checker. You are given a short host script and the ONLY "
    "facts the host was allowed to use. List every factual claim in the script, then output "
    "ONLY the claims that are NOT supported by the supplied facts (a wrong or absent year, "
    "label, producer, personnel, chart, award, or anecdote). Perceptual descriptions of how "
    "the music SOUNDS are not factual claims and are always supported. Respond with ONLY a "
    'JSON array of the unsupported claims as strings, e.g. ["released in 1979", "their third '
    'album"]. If every claim is supported, respond with exactly [].'
)


def _build_factcheck_prompt(script: str, contract) -> str:
    """Render the script + the closed-world fact contract into the adversarial prompt
    (REQ-PG-005 Tier-2). The contract's airable facts are listed so the model can flag any
    claim outside them."""
    facts: List[str] = []
    if getattr(contract, "artist", ""):
        facts.append(f"artist: {contract.artist}")
    if getattr(contract, "title", ""):
        facts.append(f"title: {contract.title}")
    if getattr(contract, "album", ""):
        facts.append(f"album: {contract.album}")
    if getattr(contract, "year", None):
        facts.append(f"year: {contract.year}")
    for g in (getattr(contract, "genres", None) or []):
        facts.append(f"genre: {g}")
    for f in (getattr(contract, "grounded_facts", None) or []):
        if isinstance(f, dict) and f.get("value"):
            facts.append(f"{f.get('predicate', 'fact')}: {f.get('value')}")
    for s in (getattr(contract, "showprep_facts", None) or []):
        if isinstance(s, dict) and (s.get("value") or s.get("quote")):
            facts.append(f"sourced: {s.get('quote') or s.get('value')}")
    fact_block = "\n".join(f"- {x}" for x in facts) or "- (no facts supplied)"
    return (
        "Script to check:\n" + script.strip() + "\n\n"
        "The ONLY facts the host was allowed to use:\n" + fact_block + "\n\n"
        "Output ONLY a JSON array of the unsupported factual claims (or [])."
    )


def adversarial_factcheck(model: str, script: str, contract) -> List[str]:
    """The Tier-2 adversarial self-check (SPEC-RADIO-PROGRAMMING-007 REQ-PG-005). NEVER raises.

    Asks the LLM to list every factual claim in ``script`` and return any NOT supported by
    the ``contract``. Returns the list of unsupported claims (empty == all supported, so the
    gate passes Tier-2). On any SDK error / quota / empty parse returns [] (fail-open: the
    deterministic Tier-1 already caught the mechanical wrong facts, and an LLM-down adversarial
    pass must not block an otherwise-clean break — never-stops)."""
    prompt = _build_factcheck_prompt(script, contract)
    try:
        text = asyncio.run(_query_text(prompt, model, system_prompt=FACTCHECK_PERSONA, caller="factcheck"))
    except Exception as exc:  # noqa: BLE001 - best-effort; never crash playout
        log_event(log, "llm.factcheck_error", error=str(exc), model=model)
        return []
    claims = _extract_string_list(text)
    log_event(log, "llm.factcheck", model=model, unsupported=len(claims))
    return claims


def _extract_string_list(text: str) -> List[str]:
    """Pull a JSON array of strings out of arbitrary model text. Returns [] on anything
    unparseable (mirrors the defensive JSON-anywhere strategy of _extract_tracks)."""
    if not text:
        return []
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip() for x in data if str(x).strip()]


# =====================================================================================
# IDENTITY layer (SPEC-RADIO-SEEDING-029 Step 2): autonomous persona-identity design.
#
# When the station MINTS a persona on its own (brain.minting), it already has a grounded
# taste charter (from brain.persona_seeding over the real library) and an unused voice. The only
# free-text choice left is the persona's IDENTITY: a display name + a short personality.
# This is the cheap "Mode A" one-shot generation - SAME tools-off, one-turn, subscription
# auth config as curation/talk so it stays cheap on the 5h quota. On ANY error / empty
# parse it returns {} and the mint falls back to a deterministic identity (never crashes).
#
# The identity is plausible flavour, NOT an on-air factual claim: the host never asserts
# un-grounded facts about itself on air (that grounding rail is enforced downstream by
# host-voice-grounding). Here we only design who the persona *is*, not what it says.
# =====================================================================================

# A short system prompt for the identity designer. Kept tight (ships in the call) and
# explicitly anti-slop / bounded so the model returns a compact, speakable identity.
IDENTITY_PERSONA = (
    "You design a single distinct radio-host persona for an autonomous freeform internet "
    "radio station. Given a musical taste territory, you invent ONE believable human host: "
    "a real-sounding display name and a SHORT personality (one or two sentences) in a warm, "
    "human, non-corporate voice - never a chirpy AI assistant. Respond with ONLY a JSON "
    "object {\"name\": ..., \"personality\": ...} - no commentary, no markdown fences."
)


def _build_identity_prompt(primary_territory: str, in_genres: List[str],
                           gender: str, age: int) -> str:
    """Turn the grounded charter anchors + assigned gender/age into a one-shot prompt.

    Only the taste TERRITORY (grounded in the real library) and the already-assigned
    gender/age constrain the design; the model fills the free-text name + personality."""
    genres = ", ".join(g for g in (in_genres or []) if g) or primary_territory or "eclectic"
    parts = [
        "Design one radio-host persona.",
        f"Primary taste territory: {primary_territory or 'eclectic'}.",
        f"Plays mostly: {genres}.",
    ]
    if gender:
        parts.append(f"Gender: {gender}.")
    if age:
        parts.append(f"Age: {age}.")
    parts.append(
        'Respond with ONLY {"name": "...", "personality": "..."}.'
    )
    return " ".join(parts)


def _extract_identity(text: str) -> Dict[str, str]:
    """Pull a {name, personality} dict out of arbitrary model text. Returns {} if nothing
    usable is found (the caller then uses a deterministic identity). Mirrors the defensive
    JSON-anywhere strategy of ``_extract_tracks``."""
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            data = None
        if isinstance(data, dict):
            name = str(data.get("name") or data.get("Name") or "").strip()
            personality = str(
                data.get("personality") or data.get("Personality")
                or data.get("pov") or ""
            ).strip()
            out: Dict[str, str] = {}
            if name:
                out["name"] = name
            if personality:
                out["personality"] = personality
            return out
    return {}


def design_persona_identity(model: str, primary_territory: str,
                            in_genres: Optional[List[str]] = None,
                            *, gender: str = "", age: int = 0) -> Dict[str, str]:
    """Design a persona IDENTITY (name + short personality) for a grounded taste territory.

    NEVER raises. Returns ``{"name": ..., "personality": ...}`` (either key may be absent),
    or ``{}`` on any SDK error / quota / empty parse so the caller (brain.minting) falls back
    to a deterministic identity. Same cheap tools-off, one-turn, subscription-auth path as
    curation/talk. The identity is plausible flavour, not an on-air factual claim."""
    prompt = _build_identity_prompt(primary_territory, in_genres or [], gender, age)
    try:
        text = asyncio.run(_query_text(prompt, model, system_prompt=IDENTITY_PERSONA, caller="identity"))
        identity = _extract_identity(text)
        if identity.get("name"):
            log_event(log, "llm.identity_designed", model=model,
                      name=identity.get("name", ""))
            return identity
        log_event(log, "llm.identity_empty_parse", model=model, raw_len=len(text or ""))
    except Exception as exc:  # noqa: BLE001 - identity design is best-effort; never crash mint
        log_event(log, "llm.identity_error", error=str(exc), model=model)
    return {}


# =====================================================================================
# SHOW-ANGLE layer (SPEC-RADIO-SHOWS-020 Group SX, REQ-SX-001): editorial-angle design.
#
# The variation engine asks the LLM to PROPOSE a fresh editorial angle for a persona,
# grounded in supplied research (Last.fm Group LF / human-DJ Group SM thread hypotheses) +
# the persona's taste. The angle is editorial INVENTION grounded in real research, NOT an
# engagement/popularity-optimized theme (inherited anti-pandering). Best-effort: on any error
# / empty parse it returns {} and the engine falls back to a taste-only angle (never stalls).
# Same cheap tools-off, one-turn, subscription-auth path as curation/talk/identity.
# =====================================================================================

# A tight system prompt for the show-angle designer. Anti-slop + anti-pandering + grounded.
SHOW_ANGLE_PERSONA = (
    "You are a radio host inventing the editorial ANGLE for your next show on an autonomous "
    "freeform station. Given your musical taste and some research leads, you propose ONE "
    "fresh, specific editorial angle (a theme/lens — e.g. 'the producers behind the sound', "
    "'1979 in one hour', 'artists adjacent to X'), grounded in the research + your taste, in "
    "your own voice — never an engagement-bait or popularity-chasing theme, never a repeat of "
    "a recent angle. Respond with ONLY a JSON object "
    '{"theme": ..., "angle": ..., "lens": ..., "talking_points": [...]} — no commentary, no '
    "markdown fences. 'lens' is a short catalog filter phrase (a genre/era/mood/tag/'similar "
    "to X'); 'talking_points' are 1-3 short grounded notes you MIGHT voice."
)


def _build_show_angle_prompt(persona_desc: str, research: Optional[List[str]],
                             recent_angles: Optional[List[str]]) -> str:
    """Turn the persona description + research leads + recent angles into a one-shot prompt.

    ``research`` are short grounded leads (Last.fm similar artists / tags, human-DJ threads);
    ``recent_angles`` are this persona's recently-run angles to AVOID repeating (REQ-SX-002)."""
    parts = [
        "Invent the editorial angle for your next show.",
        f"Your taste / who you are: {persona_desc or 'an eclectic freeform host'}.",
    ]
    leads = [r for r in (research or []) if r]
    if leads:
        parts.append("Research leads to draw on (colour, not facts to state verbatim): "
                     + "; ".join(leads[:12]) + ".")
    recent = [a for a in (recent_angles or []) if a]
    if recent:
        parts.append("Do NOT repeat the kind of these recent shows you already ran: "
                     + "; ".join(recent[:8]) + ".")
    parts.append("Return ONLY the JSON object described.")
    return "\n".join(parts)


def design_show_angle(model: str, persona_desc: str,
                      research: Optional[List[str]] = None,
                      recent_angles: Optional[List[str]] = None) -> Dict[str, Any]:
    """Design a SHOW ANGLE for a persona (SPEC-RADIO-SHOWS-020 REQ-SX-001). NEVER raises.

    Returns ``{"theme", "angle", "lens", "talking_points"}`` (keys may be absent), or ``{}``
    on any SDK error / quota / empty parse so the variation engine falls back to a taste-only
    angle. Grounded in the supplied research + the persona's taste; the angle is editorial
    invention, never engagement-optimized (inherited anti-pandering)."""
    prompt = _build_show_angle_prompt(persona_desc, research, recent_angles)
    try:
        text = asyncio.run(_query_text(prompt, model, system_prompt=SHOW_ANGLE_PERSONA, caller="show_angle"))
        angle = _extract_show_angle(text)
        if angle.get("angle") or angle.get("theme"):
            log_event(log, "llm.show_angle", model=model, theme=angle.get("theme", ""))
            return angle
        log_event(log, "llm.show_angle_empty_parse", model=model, raw_len=len(text or ""))
    except Exception as exc:  # noqa: BLE001 - angle design is best-effort; never stall the engine
        log_event(log, "llm.show_angle_error", error=str(exc), model=model)
    return {}


def _extract_show_angle(text: str) -> Dict[str, Any]:
    """Pull a {theme, angle, lens, talking_points} dict out of arbitrary model text. Returns
    {} if nothing usable is found. Mirrors the JSON-anywhere strategy of _extract_identity."""
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        data = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Any] = {}
    for key in ("theme", "angle", "lens"):
        val = str(data.get(key) or "").strip()
        if val:
            out[key] = val
    tps = data.get("talking_points") or data.get("talkingPoints") or []
    if isinstance(tps, list):
        out["talking_points"] = [str(t).strip() for t in tps if str(t).strip()]
    return out


# =====================================================================================
# MODE B — the richer, web-tools-ON show-prep / research path (SPEC-RADIO-OPS-004 Group OC,
# REQ-OC-001). This is the OCCASIONAL path: it differs from every Mode-A call above in ONE
# field — ``allowed_tools=["WebSearch"]`` instead of ``[]`` — so the model may fetch live
# facts for a themed show. The FREQUENT next-track / imaging / talk paths NEVER call this;
# they stay on the tools-off Mode-A ``_query_text`` so the subscription quota is respected
# (AC-OC-001 [HARD]: the hot path is tools-off). Like every other seam it NEVER raises and
# falls back to {} so show-prep degrades to fact-only (the grounded feed) — research is
# downstream of air, never upstream.
# =====================================================================================

# Mode B keeps the SAME minimal, subscription-auth, one-turn contract as Mode A — it only
# turns ON the web-search tool. No claude_code preset, no MCP/hooks, no permission prompts
# (WebSearch is a read-only built-in that needs no file-write permission).
_MODE_B_TOOLS = ["WebSearch"]


def _build_research_options(model: str, system_prompt: str):
    """Mode-B options: identical to the cheap Mode-A config EXCEPT web tools are ON.

    Shares the subscription-auth + custom-prompt + no-preset contract of ``_build_options``
    (so the quota stays protected) and adds ONLY ``allowed_tools=["WebSearch"]`` so an
    occasional show-prep call may fetch live facts. ``max_turns`` is raised to allow a
    tool-use round-trip; everything else is the cheap path."""
    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    child_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    child_env.setdefault("HOME", "/root")
    return ClaudeAgentOptions(
        system_prompt=system_prompt,       # plain string => custom prompt, NO claude_code preset
        allowed_tools=_MODE_B_TOOLS,        # the ONLY difference from Mode A: web search ON
        setting_sources=[],                 # do not load CLAUDE.md / settings / MCP / hooks
        max_turns=4,                        # allow a tool-use round-trip for the web fetch
        model=model,
        env=child_env,                      # ANTHROPIC_API_KEY stripped => subscription auth
    )


async def _query_research(prompt: str, model: str, system_prompt: str,
                          caller: str = "research") -> str:
    """Run a single Mode-B (web-tools-ON) query and concatenate the assistant text blocks."""
    from claude_agent_sdk import query, AssistantMessage, TextBlock  # type: ignore

    options = _build_research_options(model, system_prompt=system_prompt)
    chunks: List[str] = []
    last_usage: dict = {}
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            if getattr(message, "usage", None) and isinstance(message.usage, dict):
                last_usage = message.usage
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    result = "".join(chunks)
    _record_usage(caller, prompt, result, last_usage)
    return result


def _record_usage(caller: str, prompt: str, response: str, usage: dict) -> None:
    """ADMIN-041: record one LLM call's real token usage into the in-memory counter.

    Best-effort: a counter fault must never break an LLM query (the stream comes first)."""
    try:
        from brain.llm_counter import LLMCallCounter
        LLMCallCounter.instance().record(
            caller=caller,
            prompt=prompt,
            response=response,
            input_tokens=int((usage or {}).get("input_tokens", 0) or 0),
            output_tokens=int((usage or {}).get("output_tokens", 0) or 0),
        )
    except Exception:  # noqa: BLE001 - usage capture is observability, never load-bearing
        pass


# The Mode-B show-prep system prompt. Grounded + anti-fabrication + no-self-imitation. It
# instructs the model to fetch facts via web search and to HEDGE or OMIT anything it cannot
# verify (REQ-OC-005), and it states explicitly that the supplied recent output is an
# AVOID-LIST, never an example to imitate (REQ-OC-006).
SHOW_PREP_PERSONA = (
    "You are the research desk for an autonomous freeform radio station, preparing one "
    "themed show. Using web search, gather REAL, verifiable facts about the featured artist "
    "and theme — genre origins and movements, eras, artist/label/song history, cultural and "
    "societal context, the role the music plays in human life. Ground every factual claim in "
    "a source you actually found; if you cannot verify a claim, HEDGE it or LEAVE IT OUT — "
    "never invent a fact, a date, a quote, or a credit. The recent-output list you are given "
    "is ONLY so you AVOID repeating yourself — it is NOT an example to imitate. Respond with "
    "ONLY a JSON object "
    '{"theme": ..., "tracklist": [{"artist":...,"title":...}], "talking_points": [...]} — no '
    "commentary, no markdown fences. 'talking_points' are short framing notes (genre/cultural "
    "context), NOT hard factual assertions; the hard facts come from the verified knowledge "
    "store, not from you."
)


def _build_show_prep_prompt(artist: str, theme: str,
                            grounded_facts: Optional[List[Dict[str, Any]]],
                            avoid: Optional[List[str]]) -> str:
    """One-shot Mode-B prompt: research a featured artist/theme into show-prep depth.

    ``grounded_facts`` are the facts ALREADY verified by KNOWLEDGE-008 (passed so the model
    does not re-fetch them and so it knows what is established); ``avoid`` is the recent-output
    AVOID-LIST threaded ONLY to suppress repetition, NEVER as exemplars (REQ-OC-006)."""
    parts = [
        f"Prepare a themed show featuring {artist or 'the featured artist'}"
        + (f", theme: {theme}." if theme else "."),
        "Use web search to research it. Return ONLY the JSON object described.",
    ]
    known = [str(f.get("value", "")).strip() for f in (grounded_facts or [])
             if str(f.get("value", "")).strip()]
    if known:
        parts.append("Already-verified facts (do not re-fetch, build around these): "
                     + "; ".join(known[:12]) + ".")
    recent = [a for a in (avoid or []) if a]
    if recent:
        parts.append("Recently aired (AVOID repeating these — this is a repeat-avoidance "
                     "list, NOT examples to copy): " + "; ".join(recent[:10]) + ".")
    return "\n".join(parts)


def research_show_prep(model: str, artist: str, *, theme: str = "",
                       grounded_facts: Optional[List[Dict[str, Any]]] = None,
                       avoid: Optional[List[str]] = None) -> Dict[str, Any]:
    """Mode-B occasional show-prep research (REQ-OC-001/002/004). NEVER raises.

    Returns ``{"theme", "tracklist", "talking_points"}`` (keys may be absent), or ``{}`` on
    any SDK error / quota / empty parse so the ShowPrepper degrades to the fact-only plan
    built from the verified grounding feed. This is the ONLY web-tools-ON call in the brain;
    it is occasional by construction (only the show-prep pass invokes it)."""
    prompt = _build_show_prep_prompt(artist, theme, grounded_facts, avoid)
    try:
        text = asyncio.run(_query_research(prompt, model, system_prompt=SHOW_PREP_PERSONA))
        plan = _extract_show_angle(text)  # same {theme, talking_points, ...} JSON shape
        tracklist = _extract_tracks(text)
        if tracklist:
            plan["tracklist"] = tracklist
        if plan:
            log_event(log, "llm.show_prep", model=model, artist=artist,
                      tracks=len(tracklist), theme=plan.get("theme", ""))
            return plan
        log_event(log, "llm.show_prep_empty_parse", model=model, raw_len=len(text or ""))
    except Exception as exc:  # noqa: BLE001 - show-prep is best-effort; never stall a show
        log_event(log, "llm.show_prep_error", error=str(exc), model=model)
    return {}
