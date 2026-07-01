# Golden Shower Radio — continuous playout (Liquidsoap 2.2.x), PULL-based.
#
# Liquidsoap asks the Python brain "what's next?" via HTTP and plays it.
# This replaces the flaky telnet-push interface: no pushing, no command-server
# timeouts. The brain picks the next eligible item (music or a pre-rendered host
# talk clip) and returns a Liquidsoap `annotate:` URI carrying the brain's CLEAN
# artist/title (so players show correct ICY metadata even when a file's embedded
# tags are garbled) plus a `mix_mode` hint ("music"|"talk") that steers the
# transition below. mksafe guarantees the source never fails — a brief silence
# while the library is still filling is acceptable (continuous-operation identity,
# not a zero-gap SLA).
#
# NOW-PLAYING IS GROUND TRUTH (no lead, no stale hang): because the dynamic source
# resolves ahead (prefetch=2 for crossfade buffering), /api/next is called up to 2
# items BEFORE airtime — so the brain must NOT treat hand-out as "now playing". The
# `on_track` callback below POSTs the metadata of the item that JUST started on air
# back to the brain (POST /api/airing), and the brain sets its displayed now_playing
# from THAT. The POST runs in a background thread (thread.run, fast=false) so it never
# blocks the streaming thread / playout.
#
# TRANSITIONS (per-kind — songs finish before the host speaks):
#   • music -> music : an UNCONDITIONAL gentle ~3s crossfade (fade-out the old tail +
#                      fade-in the new head, overlapped) — the smooth segue the user
#                      asked for ("at least fade out so it doesn't cut off sharply").
#                      We do NOT use cross.smart: its dB heuristic could decide NOT to
#                      fade and hard-cut. An always-on fade guarantees no sharp cut.
#   • -> talk        : NO overlap. The outgoing song FINISHES, then the host talk clip
#                      starts dry. The voice is never buried under a song's tail.
#   • talk -> music  : clean, no overlap — the host's closing words are never cut by
#                      an incoming song; music starts after the clip ends.
# Only music->music truly crossfades; talk boundaries are clean sequences. We use the
# low-level `cross` operator with a transition that branches on the INCOMING item's
# `mix_mode` metadata (set by the brain via annotate:).

def next_track() =
  ret = http.get("http://brain:8080/api/next", timeout=6.0)
  uri = string.trim("#{ret}")
  if ret.status_code == 200 and uri != "" then
    log("playout: pulling #{uri}")
    # uri is an annotate: string (annotate:artist=...,title=...,mix_mode=...:/path).
    # request.create resolves the trailing real file path and applies the annotated
    # metadata (which overrides the file's embedded tags for ICY StreamTitle).
    [request.create(uri)]
  else
    log("playout: nothing to play yet (status #{ret.status_code})")
    []
  end
end

source = request.dynamic.list(id="gsr", prefetch=2, retry_delay=2.0, next_track)

# SKIP-028 (REQ-SC-001/002/004): harbor/TCP control input liquidsoap LISTENS ON.
# The brain POSTs to http://liquidsoap:7138/api/skip_cmd (gsr-network-only, never public).
# Liquidsoap is the command CONSUMER — it owns the input and decides what to do with it.
# REQ-SC-005: PRE-cross injection point (gsr source skip) chosen first per spec decision D-1.
# The output remains mksafe-guarded (REQ-SC-004): no skip command can silence the stream.
let _ = harbor.http.register(
  port=7138,
  method="POST",
  "/api/skip_cmd",
  fun(_request, response) ->
    begin
      source.skip()
      log("skip: forceful skip command received — advancing gsr source")
      response.status_code(200)
      response.content_type("text/plain")
      response.data("ok")
    end
)

# --- Per-kind transition --------------------------------------------------------
# `cross` hands the transition function two records {db_level, metadata, source} for
# the OUTGOING (old) and INCOMING (new) items. We branch on mix_mode:
#   new == talk  -> sequence([old, new]) : let the song finish, then talk dry.
#   old == talk  -> sequence([old, new]) : let the host finish, then music clean.
#   otherwise    -> cross.smart(...)     : music<->music gentle power-aware crossfade.
def transition(old, new) =
  new_kind = new.metadata["mix_mode"]
  old_kind = old.metadata["mix_mode"]
  if new_kind == "talk" then
    # Incoming host break: NO overlap. The outgoing song plays to its end, then the
    # talk clip starts clean — the host's voice never sits under the music's tail.
    sequence([old.source, new.source])
  elsif old_kind == "talk" then
    # Talk -> music: let the host finish; start the song clean after (no overlap, so
    # the host's closing words are not cut off by an incoming track).
    sequence([old.source, new.source])
  else
    # music -> music: an UNCONDITIONAL gentle crossfade. We deliberately do NOT use
    # cross.smart here: its dB analysis sometimes decides a crossfade is unwarranted
    # and falls through to an abrupt switch (logs "No transition: using default"),
    # which is exactly the sharp cut-off the user banned. Instead we ALWAYS fade the
    # outgoing tail out and the incoming head in and overlap them — so a music->music
    # segue can NEVER hard-cut; there is always at least a 3s gentle fade.
    # [HARD] METADATA-THROUGH-CROSSFADE. A crossfade overlaps the OUTGOING (fading-out) and
    # INCOMING (fading-in) tracks. cross() CONSUMES the incoming track's metadata during its
    # look-ahead to build this transition, so neither the ICY StreamTitle nor on_metadata
    # ever see the new song — the reported track "sticks" on the one fading OUT until the
    # next clean (talk/sequence) boundary. Fix: explicitly re-insert the INCOMING track's
    # metadata onto the crossfaded output so players + the brain grab what's fading IN.
    faded = add(
      normalize=false,
      [fade.out(duration=3.0, old.source), fade.in(duration=3.0, new.source)]
    )
    faded = insert_metadata(faded)
    # Guard against stamping an empty packet (e.g. a placeholder when the source momentarily
    # has nothing queued); only re-stamp when the incoming track actually has a title.
    if new.metadata["title"] != "" then faded.insert_metadata(new.metadata) end
    faded
  end
end

# duration = how much tail/head is buffered to compute the transition. width = the
# power-measurement window cross.smart uses. mksafe wraps the result so output.icecast
# always receives an infallible source; only a total brain stall falls through to
# brief silence.
radio = cross(duration=4.0, width=2.0, transition, source)

# --- Ground-truth now-playing report --------------------------------------------
# Fire the instant a new item starts on air. The callback MUST be fast (it runs in the
# main streaming thread), so it only assembles a tiny form body and hands the blocking
# HTTP POST to a background thread (thread.run with fast=false). Playout is never
# blocked on the brain's response.
def report_airing(m) =
  artist = m["artist"]
  title = m["title"]
  album = m["album"]
  mix_mode = m["mix_mode"]
  kind = if mix_mode == "talk" then "talk" else "music" end
  # url-encode the values for a safe x-www-form-urlencoded body. album (from id3 tags)
  # is reported alongside artist/title so the brain's now_playing + website show it.
  body =
    "artist=#{url.encode(artist)}&title=#{url.encode(title)}&album=#{url.encode(album)}&kind=#{url.encode(kind)}"
  log("playout: on air -> #{artist} - #{title} (#{kind})")
  thread.run(
    fast=false,
    fun () ->
      begin
        ignore(
          http.post(
            data=body,
            headers=[("Content-Type", "application/x-www-form-urlencoded")],
            timeout=5.0,
            "http://brain:8080/api/airing"
          )
        )
      end
  )
end

# Register the airing callback on the cross OUTPUT, using on_metadata (not on_track):
# `cross` merges/deduplicates track marks (crossfades combine two tracks into one
# continuous output), so on_track at the cross output fires unreliably. on_metadata
# fires on exactly the metadata packets that flow on to output.icecast and drive the
# ICY StreamTitle - so the brain's now_playing stays in LOCKSTEP with what listeners'
# players show = true ground truth of what is airing. The brain dedups repeat reports
# (set_on_air is idempotent), so cross's occasional duplicate metadata is harmless.
# Callback-only method form avoids the positional source/function ambiguity that the
# source.on_metadata(...) free function hits once the graph is pinned to %mp3 output.
radio.on_metadata(report_airing)
radio = mksafe(radio)

# --- Two output mounts from ONE source: compatibility vs. rich metadata ----------
#   /radio      MP3 320  — universal compatibility (Safari/iOS, hardware, cars).
#                          ICY metadata carries ONLY StreamTitle + StreamUrl (there is
#                          NO album field in the ICY protocol), and Liquidsoap 2.2.5
#                          escapes non-ASCII in ICY to HTML entities — so this mount
#                          folds the album INTO an ASCII StreamTitle (see fold_album).
#   /radio.ogg  Vorbis    — Ogg carries DISCRETE Vorbis comments (artist/title/ALBUM/…)
#                          in native UTF-8, so capable players (foobar2000, VLC, mpv,
#                          Chrome, Firefox) get a real Album column plus correct "—"
#                          and accented characters. No title fold on this mount.
# `radio` (above) is the shared base with DISCRETE metadata. The Ogg mount consumes it
# as-is; only the MP3 branch (radio_mp3) folds album into the title.

# Fold the album into the MP3 mount's ICY StreamTitle when present, so MP3 listeners still
# see the album as "Artist - Title (Album)". Runs AFTER report_airing (which already
# captured CLEAN artist/title/album for the brain/website) and is applied ONLY to the MP3
# branch. Empty-safe: an untagged track (or a talk break, album="") leaves title untouched.
#
# [HARD] ASCII-ONLY separator. Liquidsoap 2.2.x escapes every non-ASCII codepoint in the
# ICY StreamTitle to an HTML numeric entity (e.g. an em dash "—" reaches foobar2000 as the
# literal text "&#8212;"). Proven on the wire: encoding="UTF-8" does NOT change this — the
# ICY metadata-update path is charset-fixed in 2.2.5. So the separator WE inject must stay
# pure ASCII. Parentheses read cleanly and stay unambiguous vs the "artist - title" hyphen.
# (The Ogg mount has NO such limit — Vorbis comments are UTF-8, so it carries the album in
# its own field with the real characters intact.)
def fold_album(m) =
  album = m["album"]
  title = m["title"]
  if album != "" and title != "" then
    [("title", "#{title} (#{album})")]
  else
    []
  end
end
radio_mp3 = metadata.map(fold_album, radio)

# MP3 mount — universal compatibility. Album folded into the ASCII StreamTitle.
output.icecast(
  %mp3(bitrate=320),
  host="icecast",
  port=8000,
  password=environment.get("ICECAST_SOURCE_PASSWORD"),
  mount="/radio",
  name=environment.get("STATION_NAME"),
  description="Autonomous AI radio that finds, downloads and spins its own music 24/7",
  genre="Eclectic",
  radio_mp3
)

# Ogg Vorbis mount — discrete UTF-8 metadata (native Album column, real "—"/accents) for
# capable players. VBR quality=0.6 ≈ ~192 kbps: more bandwidth-efficient than the 320 MP3
# at comparable perceived quality (tunable). Uses the base `radio` source (album NOT folded
# into title — it rides in its own Vorbis comment). Not played by Safari/iOS; the website
# feature-detects and only serves this mount to Ogg-capable clients.
output.icecast(
  %vorbis(quality=0.6),
  host="icecast",
  port=8000,
  password=environment.get("ICECAST_SOURCE_PASSWORD"),
  mount="/radio.ogg",
  name=environment.get("STATION_NAME"),
  description="Autonomous AI radio that finds, downloads and spins its own music 24/7",
  genre="Eclectic",
  radio
)
