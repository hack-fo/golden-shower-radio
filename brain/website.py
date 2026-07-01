"""The station website (phase 1, static built-in page).

Served from StationState.website_html so a FUTURE phase can have an LLM rewrite it
at runtime (sandbox + validate + atomic publish + auto-rollback). The audio player
streams from Icecast at ``http://<same-host>:<port>/radio``; the now-playing area
polls /api/nowplaying every 5s.
"""

from __future__ import annotations

from .config import Config


def render_website(cfg: Config) -> str:
    name = cfg.station_name
    port = cfg.icecast_public_port
    mount = cfg.icecast_mount
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{name}</title>
<style>
  :root {{
    --bg: #0c0a06; --bg2: #0e0b07; --gold: #f5c542; --gold-soft: #c9a23a;
    --ink: #f4eddb; --muted: #978c70; --line: rgba(245,197,66,.15);
    --glass: rgba(255,255,255,.04);
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    min-height: 100vh; color: var(--ink); line-height: 1.5;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background:
      radial-gradient(1400px 700px at 50% -20%, rgba(245,197,66,.16), transparent 62%),
      linear-gradient(180deg, var(--bg2), var(--bg));
    background-attachment: fixed;
  }}
  a {{ color: inherit; }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 0 20px 80px; }}

  /* ---- hero ---- */
  header.hero {{
    position: relative; text-align: center;
    padding: 64px 16px 40px;
  }}
  .topbar {{
    position: absolute; top: 18px; right: 20px;
  }}
  .stats-link {{
    display: inline-flex; align-items: center; gap: 7px; text-decoration: none;
    color: var(--gold); font-size: 13px; font-weight: 600; letter-spacing: .02em;
    padding: 8px 14px; border: 1px solid var(--line); border-radius: 999px;
    background: var(--glass); backdrop-filter: blur(8px); transition: all .2s ease;
  }}
  .stats-link:hover {{ border-color: rgba(245,197,66,.5); background: rgba(245,197,66,.08); }}
  .logo {{
    font-size: clamp(40px, 9vw, 82px); font-weight: 800; letter-spacing: -.01em; line-height: 1.02;
    background: linear-gradient(180deg, #fff6cf 0%, var(--gold) 52%, var(--gold-soft) 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    filter: drop-shadow(0 0 44px rgba(245,197,66,.3));
  }}
  .tag {{
    color: var(--muted); margin-top: 14px; font-size: 13px;
    letter-spacing: .22em; text-transform: uppercase;
  }}

  /* ---- cards / glass ---- */
  .card {{
    background: var(--glass); border: 1px solid var(--line); border-radius: 20px;
    padding: 26px; margin: 20px 0; backdrop-filter: blur(8px);
    box-shadow: 0 18px 50px -28px rgba(0,0,0,.8);
  }}
  h2 {{
    font-size: 12px; letter-spacing: .2em; text-transform: uppercase;
    color: var(--gold-soft); margin: 0 0 16px; font-weight: 700;
  }}

  /* ---- player ---- */
  .player {{ display: flex; flex-direction: column; gap: 18px; align-items: center; }}
  .live {{
    display: inline-flex; gap: 9px; align-items: center; color: var(--gold);
    font-weight: 700; letter-spacing: .16em; text-transform: uppercase; font-size: 12px;
  }}
  .dot {{
    position: relative; width: 10px; height: 10px; border-radius: 50%; background: var(--gold);
  }}
  .dot::after {{
    content: ""; position: absolute; inset: -4px; border-radius: 50%;
    border: 2px solid rgba(245,197,66,.55);
  }}
  audio {{ width: 100%; max-width: 660px; border-radius: 12px; }}
  .streamhint {{ color: var(--muted); font-size: 12px; word-break: break-all; text-align: center; }}

  /* ---- decorative waveform ---- */
  .wave {{ display: flex; gap: 5px; align-items: flex-end; height: 30px; }}
  .wave span {{
    width: 4px; height: 30%; border-radius: 3px;
    background: linear-gradient(180deg, var(--gold), var(--gold-soft));
    opacity: .85;
  }}

  /* ---- now playing ---- */
  .now {{ transition: opacity .4s ease, transform .4s ease; }}
  .now.swap {{ opacity: 0; transform: translateY(8px); }}
  .now-title {{ font-size: clamp(22px, 4.4vw, 34px); font-weight: 700; line-height: 1.15; }}
  .now-artist {{ color: var(--ink); opacity: .82; margin-top: 6px; font-size: 17px; }}
  .now-album {{ color: var(--muted); margin-top: 4px; font-size: 13px; }}
  .badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;
    color: var(--gold); padding: 5px 11px; border: 1px solid var(--line);
    border-radius: 999px; background: rgba(245,197,66,.06); letter-spacing: .02em;
  }}

  /* ---- recent + station grid ---- */
  .grid {{ display: grid; grid-template-columns: 1.3fr 1fr; gap: 20px; }}
  @media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{
    padding: 11px 12px; margin: 0 -12px; border-radius: 12px;
    display: flex; justify-content: space-between; gap: 16px; align-items: baseline;
    border-bottom: 1px solid rgba(245,197,66,.07); transition: background .18s ease;
  }}
  li:last-child {{ border-bottom: none; }}
  li:hover {{ background: rgba(245,197,66,.05); }}
  li .a {{ color: var(--ink); font-weight: 500; }}
  li .b {{ color: var(--muted); font-size: 13px; text-align: right; flex-shrink: 0; font-variant-numeric: tabular-nums; opacity: .7; }}

  .stats-row {{ display: flex; gap: 32px; flex-wrap: wrap; }}
  .stat {{ font-size: 38px; font-weight: 800; color: var(--gold); line-height: 1; }}
  .stat-l {{ color: var(--muted); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; margin-top: 6px; }}
  .sched {{ color: var(--muted); font-style: italic; }}
  .muted {{ color: var(--muted); }}

  footer {{ text-align: center; color: var(--muted); margin-top: 40px; font-size: 12px; }}

  /* ---- motion (respect reduced-motion) ---- */
  @media (prefers-reduced-motion: no-preference) {{
    .dot {{ animation: pulse 1.8s ease-out infinite; }}
    .dot::after {{ animation: ring 1.8s ease-out infinite; }}
    .wave span {{ animation: bounce 1.1s ease-in-out infinite; }}
    .wave span:nth-child(1) {{ animation-delay: 0s; }}
    .wave span:nth-child(2) {{ animation-delay: .15s; }}
    .wave span:nth-child(3) {{ animation-delay: .3s; }}
    .wave span:nth-child(4) {{ animation-delay: .45s; }}
    .wave span:nth-child(5) {{ animation-delay: .6s; }}
  }}
  @keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(245,197,66,.55); }}
    70% {{ box-shadow: 0 0 0 10px rgba(245,197,66,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(245,197,66,0); }}
  }}
  @keyframes ring {{
    0% {{ transform: scale(.7); opacity: .9; }}
    100% {{ transform: scale(1.9); opacity: 0; }}
  }}
  @keyframes bounce {{
    0%, 100% {{ height: 22%; }}
    50% {{ height: 100%; }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <div class="topbar">
        <a href="/stats" class="stats-link" aria-label="View station analytics">&#128202; Statistics</a>
      </div>
      <div class="logo">{name}</div>
      <div class="tag">Autonomous &middot; AI-curated &middot; Always on</div>
    </header>

    <main>
      <section class="card player" aria-label="Live audio stream">
        <span class="live"><span class="dot"></span> Live</span>
        <div class="wave" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span></div>
        <audio id="player" controls preload="none" aria-label="{name} live radio stream"></audio>
        <div class="streamhint" id="streamhint"></div>
      </section>

      <section class="card" aria-label="Now playing">
        <h2>Now Playing</h2>
        <div class="now" id="now">
          <div class="now-title" id="np-title">&hellip;</div>
          <div class="now-artist" id="np-artist"></div>
          <div class="now-album" id="np-album"></div>
          <div class="badges" id="np-badges"></div>
        </div>
      </section>

      <div class="grid">
        <section class="card" aria-label="Recently played">
          <h2>Recently Played</h2>
          <ul id="recent"><li class="muted">Warming up&hellip;</li></ul>
        </section>
        <section class="card" aria-label="Station">
          <h2>Station</h2>
          <div class="stats-row">
            <div><div class="stat" id="lib">0</div><div class="stat-l">Tracks in library</div></div>
            <div><div class="stat" id="dl">0</div><div class="stat-l">Acquiring now</div></div>
          </div>
          <h2 style="margin-top:26px;">Schedule</h2>
          <div class="sched">Freeform, around the clock. Shows &amp; hosts coming soon.</div>
        </section>
      </div>
    </main>

    <footer>{name} &mdash; it finds, downloads and spins its own music, 24/7.</footer>
  </div>

<script>
  // Stream from the same host the page is served from, on the icecast port.
  // Feature-detect Ogg Vorbis (NOT iOS/Android UA sniffing, which is brittle and lies):
  // capable browsers (Chrome/Firefox/Android) get the efficient /radio.ogg mount with
  // discrete UTF-8 metadata; Safari/iOS and anything without Vorbis fall back to the
  // universal MP3 mount. The .ogg mount mirrors radio.liq's second output.icecast.
  var MP3_STREAM = "http://" + location.hostname + ":{port}{mount}";
  var OGG_STREAM = MP3_STREAM + ".ogg";
  var player = document.getElementById("player");
  var canOgg = !!(player.canPlayType && player.canPlayType('audio/ogg; codecs="vorbis"'));
  var STREAM = canOgg ? OGG_STREAM : MP3_STREAM;
  player.src = STREAM;
  document.getElementById("streamhint").textContent = STREAM + (canOgg ? "  (Ogg Vorbis)" : "  (MP3)");

  function esc(s) {{ var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }}

  // Relative "when did this play" for the Recently Played list, from the server-side
  // played_at unix timestamp (seconds). Lets a listener pinpoint "the one ~2 songs ago".
  function ago(ts) {{
    var s = Math.floor(Date.now() / 1000 - Number(ts));
    if (!isFinite(s) || s < 0) return "";
    if (s < 45) return "just now";
    var m = Math.round(s / 60);
    if (m < 60) return m + "m ago";
    var h = Math.floor(m / 60), mm = m % 60;
    return h + "h" + (mm ? " " + mm + "m" : "") + " ago";
  }}

  var lastNowKey = null;
  function nowKey(np) {{ return np ? ((np.artist || "") + "\\u0000" + (np.title || "")) : ""; }}

  function renderBadges(np) {{
    if (!np) return "";
    var out = [];
    if (np.bpm != null) out.push('<span class="badge">&#9835; ' + Math.round(np.bpm) + ' BPM</span>');
    if (np.musical_key) out.push('<span class="badge">' + esc(np.musical_key) + '</span>');
    if (np.energy != null) out.push('<span class="badge">&#9889; ' + Math.round(np.energy * 100) + '% energy</span>');
    return out.join("");
  }}

  async function poll() {{
    try {{
      var r = await fetch("/api/nowplaying", {{ cache: "no-store" }});
      if (!r.ok) return;
      var d = await r.json();
      var np = d.now_playing;

      var key = nowKey(np);
      var nowEl = document.getElementById("now");
      function paint() {{
        document.getElementById("np-title").innerHTML = np ? esc(np.title || "Untitled") : "Silence (filling the library&hellip;)";
        document.getElementById("np-artist").innerHTML = np ? esc(np.artist || "") : "";
        document.getElementById("np-album").innerHTML = (np && np.album) ? esc(np.album) : "";
        document.getElementById("np-badges").innerHTML = renderBadges(np);
      }}
      if (key !== lastNowKey) {{
        lastNowKey = key;
        nowEl.classList.add("swap");
        setTimeout(function() {{ paint(); nowEl.classList.remove("swap"); }}, 200);
      }} else {{
        paint();
      }}

      document.getElementById("lib").textContent = d.library != null ? d.library : 0;
      var dl = d.downloading || [];
      document.getElementById("dl").textContent = dl.length;

      var rec = d.recent || [];
      var ul = document.getElementById("recent");
      if (!rec.length) {{ ul.innerHTML = '<li class="muted">Nothing yet&hellip;</li>'; }}
      else {{
        ul.innerHTML = rec.slice(0, 12).map(function(t) {{
          var artist = esc(t.artist || ""), title = esc(t.title || "");
          var label = artist ? (artist + " - " + title) : title;   // conventional Artist - Title
          var when = t.played_at ? ago(t.played_at) : "";
          return '<li><span class="a">' + label + '</span><span class="b">' + when + '</span></li>';
        }}).join("");
      }}
    }} catch (e) {{ /* keep polling; the radio never stops */ }}
  }}
  poll();
  setInterval(poll, 5000);
  // A backgrounded tab gets its setInterval throttled by the browser (often to >=1/min),
  // so the page can keep showing a stale track long after the stream moved on. Force an
  // immediate refresh the instant the tab becomes visible or regains focus, so a returning
  // listener always sees the true on-air track without waiting for the throttled timer.
  document.addEventListener("visibilitychange", function() {{ if (!document.hidden) poll(); }});
  window.addEventListener("focus", poll);
</script>
</body>
</html>"""
