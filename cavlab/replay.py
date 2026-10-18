"""Offline HTML trajectory replay. No server, external assets, or GUI required.

The page embeds the recorded frames, events, summary, and the lane geometry
reported by SUMO. It replays recorded results; it does not run a controller.
"""
import json


def make_replay(output, frames, events, summary, geometry=None):
    payload = json.dumps(dict(frames=frames, events=events, summary=summary,
                              geometry=geometry or {}))
    # Escape HTML delimiters so even a user-chosen scenario name stays data.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = TEMPLATE.replace("__PAYLOAD__", payload)
    (output / "replay.html").write_text(html)


TEMPLATE = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Safe Multi-Embodied Agents | Connected vehicle replay</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0c1422;color:#edf3ff;font:16px system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:28px}header{display:flex;justify-content:space-between;gap:20px;align-items:end}
h1{font-size:28px;letter-spacing:-.8px;margin:5px 0}p{color:#b7c5d9;line-height:1.5;margin:8px 0 20px}
.tag{color:#81c7ff;font-size:12px;font-weight:700;letter-spacing:2px}.grid{display:grid;grid-template-columns:2fr 1fr;gap:18px}
.card{min-width:0;background:#141f31;border:1px solid #2b3b52;border-radius:12px;padding:18px}canvas{width:100%;display:block}
button{background:#c6e6ff;border:0;border-radius:6px;padding:9px 16px;font:inherit;cursor:pointer;color:#13243b}
.controls{display:flex;align-items:center;gap:12px;margin:14px 0}input{flex:1;min-width:0}select{padding:8px;border-radius:6px}
.stats{display:flex;gap:18px;margin:16px 0;flex-wrap:wrap}.stat strong{display:block;font-size:23px}.stat small{color:#aabdd5}
.car{border-bottom:1px solid #2b3b52;padding:12px 0;font:14px ui-monospace,monospace}.status{color:#ffcc76;min-height:25px}
.status.bad{color:#ff7b7b}h2{font-size:16px;margin:0 0 10px}.events{height:155px;overflow:auto;font:12px/1.65 ui-monospace,monospace;color:#c0d1e6}
footer{margin-top:16px;color:#9fb1c9;font-size:13px;line-height:1.6}#clock{font-variant-numeric:tabular-nums;min-width:120px}
@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:16px}header{display:block}}
</style>
<main><header><div><div class="tag">CSE 494 / 598 · SAFE MULTI-EMBODIED AGENTS</div><h1>Who may enter the intersection?</h1></div><span id="case"></span></header>
<p>Three vehicle agents, one roadside coordinator. Replay of recorded SUMO motion and simulated messages. All times are simulated seconds.</p>
<div class="stats" id="stats"></div><div class="grid"><section class="card"><canvas id="road" width="800" height="520" aria-label="Top-down intersection replay"></canvas>
<div class="controls"><button id="play">Play</button><input id="seek" aria-label="Simulation time" type="range" min="0" step="0.1"><span id="clock"></span><select id="rate" aria-label="Playback rate"><option value="1">1×</option><option selected value="3">3×</option><option value="6">6×</option></select></div>
<div class="status" id="status"></div></section><aside class="card"><h2>Vehicle state</h2><div id="cars"></div><h2 style="margin-top:22px">Coordination events</h2><div class="events" id="events"></div></aside></div>
<section class="card" style="margin-top:18px"><h2>Observed conflict-zone occupancy</h2><canvas id="timeline" width="1100" height="165" aria-label="Occupancy over simulation time"></canvas></section>
<footer>The outlined polygon is the junction reported by SUMO. Occupancy is measured from the junction's internal lanes through rear clearance on the exit lane, so a car still counts as occupying the zone shortly after leaving the polygon. Two occupied routes violate this lab's conservative exclusion rule even if their bodies do not collide. This replay does not run or validate a driving controller.</footer></main>
<script type="application/json" id="data">__PAYLOAD__</script><script>
const D=JSON.parse(document.getElementById('data').textContent), S=D.summary, G=D.geometry||{};
const colors={A:'#449dff',B:'#ffb344',C:'#4ed9a0'}, ids=['A','B','C'];
const road=document.getElementById('road'),ctx=road.getContext('2d'),tl=document.getElementById('timeline'),tc=tl.getContext('2d');
const groups=new Map();for(const f of D.frames){if(!groups.has(f.time))groups.set(f.time,[]);groups.get(f.time).push(f)}
const times=[...groups.keys()],end=times.at(-1),seek=document.getElementById('seek');seek.max=end;seek.value=0;
document.getElementById('case').textContent=S.scenario+' / '+S.mode+' / seed '+S.seed;
const wait=S.max_wait_seconds===null?'none committed':S.max_wait_seconds+' s';
for(const [v,k] of [[S.completed+'/3','Cars cleared'],[Number(S.exclusion_violation_seconds).toFixed(1)+' s','Exclusion violation'],[S.collision_pair_count,'Collision pairs'],[wait,'Max wait'],[S.all_clear_time===null?'Incomplete':S.all_clear_time+' s','All cars clear']]){const e=document.createElement('div');e.className='stat';const a=document.createElement('strong'),b=document.createElement('small');a.textContent=v;b.textContent=k;e.append(a,b);document.getElementById('stats').append(e)}
const important=D.events.filter(e=>['reservation_granted','reservation_released','lease_timeout','reject_expired_grant','commit_entry','rear_cleared','collision_pair'].includes(e.event));
function frame(t){let lo=0,hi=times.length-1;while(lo<hi){const mid=(lo+hi+1)>>1;if(times[mid]<=t+1e-9)lo=mid;else hi=mid-1}return groups.get(times[lo])}
const scale=6,xx=x=>400+x*scale,yy=y=>260-y*scale;
function poly(points,close){ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(xx(x),yy(y)):ctx.moveTo(xx(x),yy(y)));if(close)ctx.closePath()}
function drawRoads(){const lanes=G.lanes||{};const ids=Object.keys(lanes);
if(!ids.length){ctx.fillStyle='#334258';ctx.fillRect(0,yy(3.2),800,6.4*scale);ctx.fillRect(xx(-3.2),0,6.4*scale,520);return}
ctx.lineCap='butt';for(const id of ids){if(id.startsWith(':'))continue;const l=lanes[id];ctx.strokeStyle='#334258';ctx.lineWidth=l.width*scale;poly(l.shape);ctx.stroke()}
for(const id of ids){if(id.startsWith(':'))continue;const l=lanes[id];ctx.strokeStyle='#4a5b74';ctx.lineWidth=1;poly(l.shape);ctx.stroke()}
if(G.junction){ctx.fillStyle='rgba(255,191,79,.12)';poly(G.junction,true);ctx.fill();ctx.strokeStyle='#ffbf4f';ctx.lineWidth=1.5;ctx.stroke()}
ctx.setLineDash([6,8]);for(const id of ids){if(!id.startsWith(':'))continue;const l=lanes[id];ctx.strokeStyle='#8fa3bf';ctx.lineWidth=1;poly(l.shape);ctx.stroke()}ctx.setLineDash([]);
for(const [v,[gx,gy]] of Object.entries(G.gates||{})){ctx.fillStyle=colors[v];ctx.beginPath();ctx.arc(xx(gx),yy(gy),3.5,0,2*Math.PI);ctx.fill()}}
function paint(t){const fs=frame(t);ctx.clearRect(0,0,800,520);ctx.fillStyle='#111b2b';ctx.fillRect(0,0,800,520);drawRoads();
ctx.fillStyle='#9fb2cd';ctx.font='13px system-ui';ctx.fillText('WEST',24,220);ctx.fillText('EAST',730,300);ctx.fillText('NORTH',425,28);ctx.fillText('SOUTH',425,500);
if(G.junction){ctx.fillStyle='#ffbf4f';ctx.fillText('junction / conflict zone',xx(9),yy(9))}
document.getElementById('cars').replaceChildren();for(const id of ids){const f=fs.find(f=>f.vehicle===id);const div=document.createElement('div');div.className='car';div.style.color=colors[id];div.textContent=f?`${id}  ${f.phase} | ${f.speed.toFixed(1)} m/s | token ${f.epoch}${f.occupied?' | in zone':''}`:`${id}  outside view`;document.getElementById('cars').append(div);
if(!f)continue;const rad=f.angle*Math.PI/180,cx=f.x-Math.sin(rad)*2.25,cy=f.y-Math.cos(rad)*2.25;ctx.save();ctx.translate(xx(cx),yy(cy));ctx.rotate(rad);ctx.fillStyle=colors[id];ctx.fillRect(-5.4,-13.5,10.8,27);ctx.fillStyle='#e3f2ff';ctx.fillRect(-4,-8,8,6);ctx.restore();ctx.fillStyle=colors[id];ctx.font='bold 15px system-ui';ctx.fillText(id,xx(cx)+12,yy(cy)-12)}
document.getElementById('clock').textContent=t.toFixed(1)+' s simulated';const n=fs.filter(f=>f.occupied).length;const st=document.getElementById('status');st.textContent=n>1?'Exclusion violation: '+n+' cars occupy the conflict zone.':n===1?'One car occupies the conflict zone.':'Conflict zone empty.';st.className=n>1?'status bad':'status';
const ev=document.getElementById('events');ev.replaceChildren();for(const e of important.filter(e=>e.time<=t).slice(-7)){const line=document.createElement('div');line.textContent=`${e.time.toFixed(1)} ${e.actor} ${e.event}${e.epoch?' #'+e.epoch:''}${e.vehicles?' '+e.vehicles.join('+'):''}`;ev.append(line)}
tc.clearRect(0,0,1100,165);const w=1050,x0=35,px=s=>x0+s/end*w,bar=Math.max(1,S.step_seconds/end*w);
for(const [i,id]of ids.entries()){const y=18+i*27;tc.fillStyle='#afc0d7';tc.font='13px system-ui';tc.fillText(id,8,y+12);tc.fillStyle='#25344b';tc.fillRect(x0,y,w,15);tc.fillStyle=colors[id];for(const f of D.frames)if(f.vehicle===id&&f.occupied)tc.fillRect(px(f.time),y,bar,15)}
const y2=18+3*27;tc.fillStyle='#afc0d7';tc.fillText('2+',8,y2+12);tc.fillStyle='#25344b';tc.fillRect(x0,y2,w,15);tc.fillStyle='#ff5c5c';for(const e of D.events)if(e.event==='exclusion_violation')tc.fillRect(px(e.time),y2,bar,15);
tc.strokeStyle='#fff';tc.beginPath();tc.moveTo(px(t),8);tc.lineTo(px(t),y2+22);tc.stroke();tc.fillStyle='#afc0d7';tc.fillText('0 s',x0,y2+36);tc.fillText(end.toFixed(1)+' s',x0+w-30,y2+36);tc.fillText('rows: zone occupancy per car; 2+ marks sampled exclusion violations',x0+120,y2+36)}
let playing=false,last=null,playTime=0;seek.oninput=()=>{playTime=Number(seek.value);paint(playTime)};document.getElementById('play').onclick=()=>{if(playTime>=end)playTime=0;playing=!playing;document.getElementById('play').textContent=playing?'Pause':'Play'};
function animate(stamp){if(playing&&last!==null){playTime=Math.min(end,playTime+(stamp-last)/1000*Number(document.getElementById('rate').value));seek.value=playTime;paint(playTime);if(playTime>=end){playing=false;document.getElementById('play').textContent='Play'}}last=stamp;requestAnimationFrame(animate)}paint(0);requestAnimationFrame(animate);
</script></html>'''
