package web

// defaultIndex is the self-contained station homepage. It polls
// /api/nowplaying every few seconds and streams Icecast at :8000/radio. The
// stream host is derived from window.location so it works from any client.
const defaultIndex = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Golden Shower Radio</title>
<style>
  :root{
    --gold:#f5c542; --gold-dim:#b8901f; --bg:#0a0a0c; --panel:#141418;
    --panel-2:#1c1c22; --text:#ece8df; --muted:#8a857a; --line:#2a2a32;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{
    background:radial-gradient(1200px 600px at 50% -10%, #1a160a 0%, var(--bg) 55%);
    color:var(--text);
    font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    min-height:100vh; display:flex; flex-direction:column; align-items:center;
  }
  .wrap{width:100%; max-width:720px; padding:32px 20px 64px}
  header{text-align:center; margin-bottom:28px}
  .logo{
    font-size:40px; font-weight:800; letter-spacing:-.5px; line-height:1.05;
    background:linear-gradient(180deg,var(--gold),var(--gold-dim));
    -webkit-background-clip:text; background-clip:text; color:transparent;
    text-shadow:0 0 40px rgba(245,197,66,.25);
  }
  .tagline{color:var(--muted); margin-top:8px; font-style:italic; font-size:14px}
  .dot{display:inline-block;width:9px;height:9px;border-radius:50%;
    background:var(--gold); box-shadow:0 0 10px var(--gold); margin-right:7px;
    animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  .live{display:inline-flex;align-items:center;color:var(--gold);font-size:12px;
    text-transform:uppercase;letter-spacing:2px;margin-top:14px}
  .card{
    background:linear-gradient(180deg,var(--panel),var(--panel-2));
    border:1px solid var(--line); border-radius:16px; padding:22px;
    margin-bottom:18px; box-shadow:0 10px 40px rgba(0,0,0,.4);
  }
  .nowlabel{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--gold-dim)}
  .nowtrack{font-size:22px;font-weight:700;margin-top:6px;min-height:30px}
  audio{width:100%;margin-top:18px;border-radius:10px;outline:none}
  audio::-webkit-media-controls-panel{background:var(--panel-2)}
  .stats{display:flex;gap:14px;margin-top:4px}
  .stat{flex:1;text-align:center;background:var(--panel-2);border:1px solid var(--line);
    border-radius:12px;padding:14px}
  .statnum{font-size:26px;font-weight:800;color:var(--gold)}
  .statlbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-top:2px}
  h2{font-size:13px;text-transform:uppercase;letter-spacing:2px;color:var(--gold-dim);
    margin-bottom:12px}
  ul{list-style:none}
  li{padding:9px 0;border-bottom:1px solid var(--line);color:var(--text);font-size:15px;
    display:flex;align-items:center}
  li:last-child{border-bottom:none}
  li .idx{color:var(--gold-dim);width:26px;font-variant-numeric:tabular-nums;font-size:13px}
  .empty{color:var(--muted);font-style:italic;font-size:14px}
  .dl{color:var(--muted);font-size:13px}
  .dl .spin{color:var(--gold)}
  footer{color:var(--muted);font-size:12px;text-align:center;margin-top:10px}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo">Golden&nbsp;Shower&nbsp;Radio</div>
      <div class="tagline">Autonomous late-night curation. No ads. No algorithm. Just the good stuff, all night.</div>
      <div class="live"><span class="dot"></span>On Air</div>
    </header>

    <div class="card">
      <div class="nowlabel">Now Playing</div>
      <div class="nowtrack" id="now">&hellip;</div>
      <audio id="player" controls preload="none"></audio>
    </div>

    <div class="stats">
      <div class="stat"><div class="statnum" id="libcount">0</div><div class="statlbl">Tracks</div></div>
      <div class="stat"><div class="statnum" id="queue">0</div><div class="statlbl">Queued</div></div>
      <div class="stat"><div class="statnum" id="dlcount">0</div><div class="statlbl">Acquiring</div></div>
    </div>

    <div class="card">
      <h2>Recently Played</h2>
      <ul id="recent"><li class="empty">warming up&hellip;</li></ul>
    </div>

    <div class="card" id="dlcard" style="display:none">
      <h2>Now Acquiring</h2>
      <ul id="downloading"></ul>
    </div>

    <footer>Powered by a tasteful machine &middot; streaming via Icecast</footer>
  </div>

<script>
(function(){
  var host = window.location.hostname || "localhost";
  var player = document.getElementById("player");
  player.src = "http://" + host + ":8000/radio";

  function esc(s){var d=document.createElement("div");d.textContent=s;return d.innerHTML;}

  function render(d){
    document.getElementById("now").innerHTML = d.now_playing ? esc(d.now_playing) : "&mdash;";
    document.getElementById("libcount").textContent = d.library || 0;
    document.getElementById("queue").textContent = d.queue_depth || 0;
    var dl = d.downloading || [];
    document.getElementById("dlcount").textContent = dl.length;

    var recent = d.recent || [];
    var ul = document.getElementById("recent");
    if(!recent.length){ ul.innerHTML = '<li class="empty">nothing yet &mdash; the station is acquiring its first tracks</li>'; }
    else {
      ul.innerHTML = recent.map(function(t,i){
        return '<li><span class="idx">'+(i+1)+'</span>'+esc(t)+'</li>';
      }).join("");
    }

    var dcard = document.getElementById("dlcard");
    var dul = document.getElementById("downloading");
    if(dl.length){
      dcard.style.display="block";
      dul.innerHTML = dl.map(function(t){
        return '<li><span class="spin">&#9679;</span>&nbsp;'+esc(t)+'</li>';
      }).join("");
    } else { dcard.style.display="none"; }
  }

  function poll(){
    fetch("/api/nowplaying",{cache:"no-store"})
      .then(function(r){return r.json();})
      .then(render)
      .catch(function(){});
  }
  poll();
  setInterval(poll, 5000);
})();
</script>
</body>
</html>`
