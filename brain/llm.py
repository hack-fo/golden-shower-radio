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
from typing import Dict, List, Optional

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

    # Hand the CLI a copy of the environment WITHOUT ANTHROPIC_API_KEY so it uses
    # the subscription OAuth creds, never pay-per-use credits. Keep HOME so the SDK
    # finds /root/.claude.
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
        env=child_env,                # ANTHROPIC_API_KEY stripped => subscription auth
    )


async def _query_text(prompt: str, model: str, system_prompt: str = PERSONA) -> str:
    """Run a single one-shot query and concatenate the assistant text blocks.

    ``system_prompt`` chooses the persona (curator vs on-air host)."""
    from claude_agent_sdk import query, AssistantMessage, TextBlock  # type: ignore

    options = _build_options(model, system_prompt=system_prompt)
    chunks: List[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return "".join(chunks)


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


def _build_prompt(batch_size: int, recent: List[str], seed_reference: List[str]) -> str:
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
    return "\n".join(parts)


def curate_batch(
    model: str,
    batch_size: int = 25,
    recent: Optional[List[str]] = None,
    seed_reference: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Return a batch of {artist, title} dicts. NEVER raises; always returns >=1.

    On any SDK error / quota / rate-limit / empty parse, falls back to the built-in
    seed list (shuffled) so the station keeps running.
    """
    recent = recent or []
    seed_reference = seed_reference or []
    prompt = _build_prompt(batch_size, recent, seed_reference)

    try:
        text = asyncio.run(_query_text(prompt, model))
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


def _build_talk_prompt(context: Dict) -> str:
    """Turn a talk context dict into a single one-shot prompt for the host persona.

    Recognised keys (all optional):
      last_artist / last_title  - the track that just finished (for a back-announce)
      next_artist / next_title  - the upcoming track (for an intro)
      station_name              - station identity, for the occasional ident
      grounded_facts            - KNOWLEDGE-008 verified facts (REQ-KI-001): a list of
                                  {predicate, value, certain, hedge, ...}. CERTAIN facts may
                                  be stated plainly; QUALIFIED facts MUST carry their hedge.
      grounded_relations        - KNOWLEDGE-008 real graph edges (REQ-KG-004): a list of
                                  {rel, target, ...} the host may segue on (real edges only).
    """
    last_artist = str(context.get("last_artist") or "").strip()
    last_title = str(context.get("last_title") or "").strip()
    next_artist = str(context.get("next_artist") or "").strip()
    next_title = str(context.get("next_title") or "").strip()
    station = str(context.get("station_name") or "").strip()

    parts: List[str] = [
        "Write a SHORT spoken radio link to say between songs, right now, live on air.",
        "One to three sentences. Natural spoken English. Output ONLY the words to say - "
        "no quotes, no markdown, no stage directions, no song metadata formatting.",
    ]
    if last_artist or last_title:
        parts.append(f"You just played: \"{last_title}\" by {last_artist}." if last_artist
                     else f"You just played: \"{last_title}\".")
        parts.append("Briefly back-announce it (a touch of character or a tasteful aside is welcome).")
    if next_artist or next_title:
        parts.append(f"Coming up next: \"{next_title}\" by {next_artist}." if next_artist
                     else f"Coming up next: \"{next_title}\".")
        parts.append("Intro it naturally - name the artist and title so listeners know what they're hearing.")
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
    parts.append("Keep it tight - this is a link, not a monologue.")
    return "\n".join(parts)


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


def generate_talk_script(model: str, context: Dict) -> str:
    """Generate a SHORT host talk link for the given context. NEVER raises.

    Returns the clean spoken text, or "" on any SDK error / quota / empty parse so the
    caller can skip the talk break and just play the next song. Cheap by design: same
    tools-off, one-turn, subscription-auth config as curation, with a HOST system prompt.
    """
    prompt = _build_talk_prompt(context)
    try:
        text = asyncio.run(_query_text(prompt, model, system_prompt=HOST_PERSONA))
        spoken = _clean_talk_text(text)
        if spoken:
            log_event(log, "llm.talk_script", model=model, chars=len(spoken))
            return spoken
        log_event(log, "llm.talk_empty_parse", model=model, raw_len=len(text or ""))
    except Exception as exc:  # noqa: BLE001 - talk is best-effort; never crash playout
        log_event(log, "llm.talk_error", error=str(exc), model=model)
    return ""
