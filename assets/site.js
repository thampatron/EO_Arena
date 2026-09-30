// Shared chrome and helpers for all pages.
const REPO = "https://github.com/thampatron/EO_Arena";
const PAGES = [["index.html","Explorer"],["map.html","Map"],["tasks.html","Tasks"],["arena.html","Arena"],["domains.html","Domains"],["sensors.html","Sensors"],["about.html","About"]];
const TIER = {open:["t-open","Open"],reg:["t-reg","Free + terms"],nc:["t-nc","Non-commercial"],unk:["t-unk","Licence unverified"],closed:["t-closed","Restricted"]};
const STATUS = {sat:["s-sat","Saturated"],cov:["s-cov","Covered"],thin:["s-thin","Thin"],gap:["s-gap","Gap"]};
const flag = s => String(s ?? "").replace(/UNVERIFIED/g,'<span class="flag">UNVERIFIED</span>');
const esc = s => String(s ?? "").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const chip = (cls,label) => `<span class="chip ${cls}">${label}</span>`;
const tierChip = t => chip(...TIER[t]);
const statusChip = s => chip(...STATUS[s]);
const dots = n => '<span class="dots" aria-hidden="true">'+[1,2,3].map(i=>`<i class="${i<=Math.min(3,n)?'on':''}"></i>`).join('')+'</span>';
const chev = '<svg class="chev" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
async function loadJSON(...names){
  try { return await Promise.all(names.map(n=>fetch(`data/${n.includes(".")?n:n+".json"}`).then(r=>{if(!r.ok)throw 0;return r.json();}))); }
  catch(e){ const m=document.querySelector('main'); if(m) m.innerHTML='<p class="lead" style="padding:48px 0">The data files could not be loaded. If you opened this page from disk, serve the folder instead: <code>python3 -m http.server</code>.</p>'; throw e; }
}
function chrome(){
  const here = location.pathname.split('/').pop() || 'index.html';
  const nav = document.createElement('header'); nav.className='nav';
  nav.innerHTML = `<div class="nav-in"><a class="brand" href="index.html">EOArena</a><span class="badge-draft">Draft v0.2</span><nav class="nav-links" aria-label="Site">${PAGES.map(([h,l])=>`<a href="${h}"${h===here?' aria-current="page"':''}>${l}</a>`).join('')}<a href="${REPO}">GitHub</a></nav></div>`;
  document.body.prepend(nav);
  const f = document.createElement('footer'); f.className='foot';
  f.innerHTML = `<div><span>EOArena task taxonomy · Earth Intelligence Lab, MIT</span><span>Data CC BY 4.0 · Code MIT · Datasets keep their providers' licences · <a href="${REPO}/issues">Report a correction</a></span></div>`;
  document.body.append(f);
}
chrome();
