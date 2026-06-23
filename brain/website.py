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
<title>{name}</title>
<style>
  :root {{
    --bg: #0c0a06; --bg2: #141008; --gold: #f5c542; --gold-soft: #c9a23a;
    --ink: #f3ecd9; --muted: #8c8268; --line: #2a2113;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    color: var(--ink);
    background:
      radial-gradient(1200px 600px at 50% -10%, rgba(245,197,66,.12), transparent 60%),
      linear-gradient(180deg, var(--bg2), var(--bg));
  }}
  .wrap {{ max-width: 920px; margin: 0 auto; padding: 40px 20px 80px; }}
  header {{ text-align: center; margin-bottom: 28px; }}
  .logo {{
    font-size: clamp(34px, 7vw, 64px); font-weight: 800; letter-spacing: .02em; line-height: 1;
    background: linear-gradient(180deg, #fff3c4, var(--gold) 55%, var(--gold-soft));
    -webkit-background-clip: text; background-clip: text; color: transparent;
    text-shadow: 0 0 40px rgba(245,197,66,.25);
  }}
  .tag {{ color: var(--muted); margin-top: 10px; font-size: 14px; letter-spacing: .14em; text-transform: uppercase; }}
  .card {{
    background: rgba(255,255,255,.03); border: 1px solid var(--line); border-radius: 16px;
    padding: 22px; margin: 18px 0; backdrop-filter: blur(6px);
  }}
  .player {{ display: flex; flex-direction: column; gap: 14px; align-items: center; }}
  audio {{ width: 100%; max-width: 640px; }}
  .live {{
    display: inline-flex; gap: 8px; align-items: center; color: var(--gold);
    font-weight: 700; letter-spacing: .12em; text-transform: uppercase; font-size: 12px;
  }}
  .dot {{ width: 9px; height: 9px; border-radius: 50%; background: var(--gold);
    box-shadow: 0 0 0 0 rgba(245,197,66,.6); animation: pulse 1.8s infinite; }}
  @keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(245,197,66,.6); }} 70% {{ box-shadow: 0 0 0 12px rgba(245,197,66,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(245,197,66,0); }} }}
  h2 {{ font-size: 13px; letter-spacing: .16em; text-transform: uppercase; color: var(--gold-soft); margin: 0 0 12px; }}
  .now-title {{ font-size: clamp(20px, 4vw, 30px); font-weight: 700; }}
  .now-artist {{ color: var(--muted); margin-top: 4px; font-size: 16px; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ padding: 9px 0; border-bottom: 1px dashed var(--line); display: flex; justify-content: space-between; gap: 16px; }}
  li:last-child {{ border-bottom: none; }}
  li .a {{ color: var(--ink); }} li .b {{ color: var(--muted); }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
  @media (max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .stat {{ font-size: 30px; font-weight: 800; color: var(--gold); }}
  .stat-l {{ color: var(--muted); font-size: 12px; letter-spacing: .14em; text-transform: uppercase; }}
  .muted {{ color: var(--muted); }}
  footer {{ text-align: center; color: var(--muted); margin-top: 30px; font-size: 12px; }}
  .sched {{ color: var(--muted); font-style: italic; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo">{name}</div>
      <div class="tag">Autonomous &middot; AI-curated &middot; Always on</div>
    </header>

    <div class="card player">
      <span class="live"><span class="dot"></span> Live</span>
      <audio id="player" controls preload="none"></audio>
      <div class="muted" id="streamhint"></div>
    </div>

    <div class="card">
      <h2>Now Playing</h2>
      <div class="now-title" id="np-title">&hellip;</div>
      <div class="now-artist" id="np-artist"></div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>Recently Played</h2>
        <ul id="recent"><li class="muted">Warming up&hellip;</li></ul>
      </div>
      <div class="card">
        <h2>Station</h2>
        <div style="display:flex; gap:28px; flex-wrap:wrap;">
          <div><div class="stat" id="lib">0</div><div class="stat-l">Tracks in library</div></div>
          <div><div class="stat" id="dl">0</div><div class="stat-l">Acquiring now</div></div>
        </div>
        <h2 style="margin-top:22px;">Schedule</h2>
        <div class="sched">Freeform, around the clock. Shows &amp; hosts coming soon.</div>
      </div>
    </div>

    <footer>{name} &mdash; it finds, downloads and spins its own music, 24/7.</footer>
  </div>

<script>
  // Stream from the same host the page is served from, on the icecast port.
  var STREAM = "http://" + location.hostname + ":{port}{mount}";
  var player = document.getElementById("player");
  player.src = STREAM;
  document.getElementById("streamhint").textContent = STREAM;

  function esc(s) {{ var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }}

  async function poll() {{
    try {{
      var r = await fetch("/api/nowplaying", {{ cache: "no-store" }});
      if (!r.ok) return;
      var d = await r.json();
      var np = d.now_playing;
      document.getElementById("np-title").innerHTML = np ? esc(np.title || "Untitled") : "Silence (filling the library&hellip;)";
      document.getElementById("np-artist").innerHTML = np ? esc(np.artist || "") : "";
      document.getElementById("lib").textContent = d.library != null ? d.library : 0;
      var dl = d.downloading || [];
      document.getElementById("dl").textContent = dl.length;
      var rec = d.recent || [];
      var ul = document.getElementById("recent");
      if (!rec.length) {{ ul.innerHTML = '<li class="muted">Nothing yet&hellip;</li>'; }}
      else {{
        ul.innerHTML = rec.slice(0, 12).map(function(t) {{
          return '<li><span class="a">' + esc(t.title || "") + '</span><span class="b">' + esc(t.artist || "") + '</span></li>';
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
