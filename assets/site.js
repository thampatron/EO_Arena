// Shared chrome and helpers for all pages.
const REPO = "https://github.com/thampatron/EO_Arena";
const PAGES = [["index.html","Explorer"],["map.html","Map"],["benchmarks.html","Benchmark ranking"],["evidence.html","Evidence map"],["domains.html","Domains"],["sensors.html","Sensors"],["about.html","About"]];
const TIER = {open:["t-open","Open"],reg:["t-reg","Free + terms"],nc:["t-nc","Non-commercial"],unk:["t-unk","Licence unverified"],closed:["t-closed","Restricted"]};
const STATUS = {sat:["s-sat","Heavily benchmarked"],cov:["s-cov","Covered"],thin:["s-thin","Thin"],gap:["s-gap","Gap"]};
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
  nav.innerHTML = `<div class="nav-in"><a class="brand" href="index.html">EOArena</a><span class="badge-draft">Draft v0.3</span><nav class="nav-links" aria-label="Site">${PAGES.map(([h,l])=>`<a href="${h}"${h===here?' aria-current="page"':''}>${l}</a>`).join('')}<a href="${REPO}">GitHub</a></nav></div>`;
  document.body.prepend(nav);
  const f = document.createElement('footer'); f.className='foot';
  f.innerHTML = `<div><span>EOArena task taxonomy · Earth Intelligence Lab, MIT</span><span>Data CC BY 4.0 · Code MIT · Datasets keep their providers' licences · <a href="${REPO}/issues">Report a correction</a></span></div>`;
  document.body.append(f);
}
chrome();

// ---------------------------------------------------------------------------------------------------------------------
// Metric definitions for the GeoFM evidence (benchmarks.html, index.html). One registry so every page says the same
// thing. Each entry: name, what (definition), how (exactly how it is computed in scripts/build_evidence.py and
// scripts/geofm_scoring.py), and the source equation in S. Wang, "GeoFM Benchmark Scoring" (Oct 2026).
const METRICS = {
  models:{name:"Models",what:"Number of distinct foundation models with a published score on this benchmark.",how:"Counted over the benchmark's comparisons after removing numbers copied from other papers, ablation variants, non-foundation baselines and models trained from scratch."},
  papers:{name:"Papers",what:"Number of distinct papers that reported scores on this benchmark. With a single paper, the score describes one group's evaluation; it does not show that other groups would separate the models the same way.",how:"Distinct source papers over the benchmark's comparisons."},
  tasks_n:{name:"Comparisons",what:"Number of separate model comparisons behind the row. A comparison is one paper's table of at least four models evaluated on the same benchmark version, adaptation protocol, metric and training-label fraction.",how:"Grouped by paper × benchmark version × protocol × metric × label fraction, keeping groups with ≥ 4 models. The paper stands in for implementation details (decoder, split) that are not recorded separately.",eq:"Note §1, 'task'"},
  results:{name:"Reported results",what:"Number of individual published scores behind the row.",how:"Rows in the meta-analysis table after the exclusions listed under Models."},
  spread_pts:{name:"Spread",what:"How far apart the models are on this benchmark: the standard deviation of model scores within a comparison, in metric points (e.g. mIoU or accuracy points).",how:"√τ²_obs, with τ²_obs the variance of the reported scores across models in a comparison, averaged over comparisons weighted by their number of models. Shown for percentage metrics only.",eq:"Eq. 10"},
  noise_sd:{name:"Seed noise",what:"How much one model's score changes when the same evaluation is simply run again (different random seed or initialisation), in metric points.",how:"Measured: the standard deviation that papers print for each model (\"mean ± sd\", or the per-seed values of the GEO-Bench-2 leaderboard), combined across the models of a comparison by the median of the variances; requires ≥ 3 models with a printed value. Estimated: when no paper prints it, the measured value from the same dataset, protocol and metric is used if available, otherwise the median measured value for that protocol (about 0.6–0.7 points). Estimated values are labelled.",eq:"Eq. 1, σ²"},
  n_reps:{name:"Runs per value",what:"How many runs each published score averages. An average over n runs carries noise σ²/n, so the correction of the spread depends on it.",how:"The number of listed seeds when a score lists them (5 on GEO-Bench-2); otherwise the number stated in the paper (e.g. Prithvi-v2 10, GeoCrossBench 5); otherwise 3, marked as assumed. With estimated noise, 1 is used."},
  score:{name:"Score",what:"The share of the differences between models that is real rather than evaluation noise, from 0 to 1. At 0.9, 90% of the spread between models would reappear if the evaluation were run again; at 0.5, half of it is noise. The main quantity on this page; the 90% confidence interval follows in brackets.",how:"For each comparison: stable variance τ² = τ²_obs − σ²/n (spread minus the noise contained in the published averages), then score = τ²/(τ² + σ²). For the benchmark: the average over comparisons weighted by number of models, using comparisons with measured noise when any exist. Interval: 200 bootstrap resamples of the models in each comparison, centred on the estimate.",eq:"Eq. 6"},
  score_top:{name:"Top-half score",what:"The same score, computed only among the better half of the models in each comparison. It answers whether the benchmark still distinguishes strong models from each other, rather than strong models from weak baselines. A large drop from Score means the benchmark mainly separates weak from strong. 90% interval in brackets.",how:"Keep the top ⌈n/2⌉ models of each comparison (at least 4), recompute the spread on them and apply the same formula and noise. Not shown for comparisons with exactly 4 models. An extension of the note, not part of it."},
  edi:{name:"Signal-to-noise (EDI)",what:"Effective discriminative information: stable differences between models divided by seed noise. Unbounded; Score is EDI/(1 + EDI). Useful only to order benchmarks whose scores are all close to 1.",how:"EDI = score/(1 − score) from the benchmark's score.",eq:"Eq. 4"},
  unexplained_share:{name:"Dataset-specific signal",what:"How much of this benchmark's ranking of models is its own, rather than shared with other benchmarks. High: the benchmark orders models in a way others do not. A description, not a quality judgement.",how:"From a latent-factor model fitted to all comparisons (three shared factors): the share of the stable between-model variance that the shared factors leave unexplained.",eq:"Eq. 5"},
  info_share:{name:"Information share",what:"How much this benchmark adds to what the whole collection reveals about models, with credit split between benchmarks that measure the same thing. Intended for choosing a suite. Currently over-credits benchmarks with many comparisons; treat as indicative.",how:"Shapley share of log det(I + ΛᵀC⁻¹Λ) from the latent-factor model, over datasets.",eq:"Eq. 7–8"},
  self_share:{name:"Self-reported",what:"Share of the scores that come from the paper that introduced the model being scored.",how:"Weighted average over the benchmark's comparisons. Not used in the score; the Advanced settings can recompute everything without these scores."},
  suites:{name:"Suites",what:"Number of published benchmark suites that already include this dataset (e.g. PANGAEA, GEO-Bench, GEO-Bench-2, Copernicus-Bench). Hover the number for the list. Datasets in several suites are widely recognised.",how:"From the EOArena dataset inventory. Shows – for datasets not yet in the inventory."},
  verdict:{name:"Verdict",what:"A summary of the score and of how the seed noise was obtained.",how:"Reliable: score ≥ 0.8, noise measured. Moderate: 0.5–0.8, measured. Unreliable: below 0.5, measured. Likely reliable / Uncertain: score ≥ 0.8 / below 0.8 with estimated noise. No noise data: spread known, noise neither printed nor estimable. Too few models: no comparison has four models. The table is ordered by verdict, then by number of papers, then by score."},
  r2_shared:{name:"Shared-factor R²",what:"Share of the spread on this benchmark reproduced by the shared factors of the latent-factor model.",how:"1 − residual variance / observed variance, averaged over comparisons."},
  protocol:{name:"Protocol",what:"How the foundation model was adapted to the task. Frozen: the pretrained encoder is kept fixed and only a small head (linear probe, k-NN or decoder) is trained. Fine-tuned: the whole model is trained on the task.",how:"Linear probe, k-NN, frozen encoder + decoder → frozen; full or partial fine-tuning → fine-tuned."},
};function infoIcon(key){const m=METRICS[key];if(!m)return '';return `<button type="button" class="info" data-m="${key}" aria-label="About ${esc(m.name)}">i</button>`;}
function infoPop(key){
  closeInfo();const m=METRICS[key];if(!m)return;const d=m.detail||{};
  const sec=(h,body)=>body?`<section><h3>${h}</h3>${body}</section>`:'';
  const list=a=>a&&a.length?`<ol>${a.map(x=>`<li>${x}</li>`).join('')}</ol>`:'';
  const ul=a=>a&&a.length?`<ul>${a.map(x=>`<li>${x}</li>`).join('')}</ul>`:'';
  const ov=document.createElement('div');ov.className='mdl-ov';ov.setAttribute('role','dialog');ov.setAttribute('aria-modal','true');ov.setAttribute('aria-label',m.name);
  ov.innerHTML=`<div class="mdl"><header><div><p class="mdl-k">How this number is made</p><h2>${esc(m.name)}</h2></div><button type="button" class="mdl-x" aria-label="Close">×</button></header><div class="mdl-b">
   ${sec('What it means',`<p>${d.meaning||esc(m.what)}</p>`)}
   ${sec('How it is computed',d.steps?list(d.steps):`<p>${esc(m.how||'')}</p>`)}
   ${sec('Formula',d.formula?`<p class="mdl-f">${d.formula}</p>`:'')}
   ${sec('Worked example',d.example?`<p>${d.example}</p>`:'')}
   ${sec('Edge cases and choices made',ul(d.edge))}
   ${sec('Settings that change it',d.settings?`<p>${d.settings}</p>`:'')}
   ${sec('Source',d.source?`<p>${d.source} Method: S. Wang, <i>GeoFM Benchmark Scoring</i> (2026). Code: <code>scripts/geofm_scoring.py</code>, <code>scripts/build_evidence.py</code>.</p>`:'')}
  </div></div>`;
  document.body.append(ov);document.body.classList.add('mdl-open');
  ov.addEventListener('click',e=>{if(e.target===ov||e.target.closest('.mdl-x'))closeInfo();});
  ov.querySelector('.mdl-x').focus();
}
function closeInfo(){document.querySelectorAll('.mdl-ov,.pop').forEach(p=>p.remove());document.body.classList.remove('mdl-open');}
document.addEventListener('click',e=>{const b=e.target.closest('button.info[data-m]');if(b){e.stopPropagation();e.preventDefault();infoPop(b.dataset.m);return;}});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeInfo();});

// ---------------------------------------------------------------------------------------------------------------------
// Analysis settings shared by the evidence pages: which variant of the scoring to show. Stored in the URL (so a view
// can be shared) and in localStorage (so it follows the reader between pages).
const SETTINGS_DEF = {
  headline:{label:"Score computed among",options:[["score","all models","Standard score: all models in each comparison."],["score_top","the top half of models","Top-half score drives the verdict and the order: whether the benchmark separates strong models from each other."]]},
  self:{label:"Scores from a model's own paper",options:[["all","included","All published scores are used."],["independent","excluded","Scores reported by the paper that introduced the model are removed before anything is computed; comparisons left with fewer than 4 models are dropped."]]},
  unit:{label:"One row per",options:[["dataset","dataset","Each dataset is scored once over all its comparisons."],["protocol","dataset and protocol","Frozen and fine-tuned evaluations of a dataset are scored separately."]]},
  noise:{label:"Seed noise combined by",options:[["median","median across models","Robust to a single unusually unstable model."],["mean","mean across models","Pooled estimate; one unstable model can dominate it."]]},
  ridge:{label:"Latent-factor model",options:[["10","stable fit","Stronger regularisation; the result is reproducible under resampling. Used by default."],["3","predictive fit","Weaker regularisation; predicts held-out scores slightly better but changes under resampling. Affects only dataset-specific signal and information share."]]},
};
const SETTINGS_DEFAULT={noise:"median",self:"all",headline:"score",unit:"dataset",ridge:"10"};
const SET={...SETTINGS_DEFAULT};
(function(){try{Object.assign(SET,JSON.parse(localStorage.getItem("eoarena.settings")||"{}"));}catch(e){}
  const u=new URLSearchParams(location.search);Object.keys(SETTINGS_DEF).forEach(k=>{if(u.has("s_"+k))SET[k]=u.get("s_"+k);});
  Object.keys(SETTINGS_DEF).forEach(k=>{if(!SETTINGS_DEF[k].options.some(o=>o[0]===SET[k]))SET[k]=SETTINGS_DEFAULT[k];});})();
function settingsSave(){try{localStorage.setItem("eoarena.settings",JSON.stringify(SET));}catch(e){}
  const u=new URLSearchParams(location.search);Object.keys(SETTINGS_DEF).forEach(k=>{if(SET[k]!==SETTINGS_DEFAULT[k])u.set("s_"+k,SET[k]);else u.delete("s_"+k);});history.replaceState(null,"",location.pathname+(u.toString()?"?"+u:""));}
const variantKey=()=>`${SET.noise}|${SET.self}`;
const isDefaultSettings=()=>Object.keys(SETTINGS_DEF).every(k=>SET[k]===SETTINGS_DEFAULT[k]);
function settingsSummary(){return Object.keys(SETTINGS_DEF).filter(k=>SET[k]!==SETTINGS_DEFAULT[k]).map(k=>`${SETTINGS_DEF[k].label} ${SETTINGS_DEF[k].options.find(o=>o[0]===SET[k])[1]}`).join("; ");}
// Overlay the chosen variant on an evidence record. Returns a new object; the main-variant fields stay as *_main.
function applyVariant(e){
  if(!e)return e;const o={...e,score_main:e.score,verdict_main:e.verdict};
  const vk=variantKey();
  if(vk!=="median|all"&&e.variants&&e.variants[vk]){const v=e.variants[vk];["tasks_n","models","papers","results","spread_pts","noise_sd","n_sd_models","sigma2_source","sigma2","score","score_lo","score_hi","score_top","score_top_lo","score_top_hi","edi","edi_top","n_reps","n_reps_known","score_all","self_share","verdict"].forEach(k=>{if(k in v)o[k]=v[k];});o.variant=vk;}
  if(SET.ridge!=="10"&&e.latent_variants&&e.latent_variants[SET.ridge]){const l=e.latent_variants[SET.ridge];["unexplained_share","r2_shared","info_share"].forEach(k=>{if(k in l)o[k]=l[k];});}
  if(SET.headline==="score_top"&&o.score_top!=null){o.score_full=o.score;o.score_full_lo=o.score_lo;o.score_full_hi=o.score_hi;o.edi_full=o.edi;o.score=o.score_top;o.score_lo=o.score_top_lo??null;o.score_hi=o.score_top_hi??null;o.edi=o.edi_top;o.verdict=reVerdict(o);}
  else if(SET.headline==="score_top"&&o.score!=null){o.score=null;o.edi=null;o.verdict=reVerdict(o);}
  if(vk!=="median|all"&&o.variant)o.verdict=reVerdict(o);
  return o;}
function reVerdict(o){if((o.models||0)<4||!o.tasks_n)return "e_few";if(o.score==null)return "e_spread";if(o.sigma2_source==="measured")return o.score>=0.8?"e_reliable":o.score>=0.5?"e_moderate":"e_weak";return o.score>=0.8?"e_prov_high":"e_prov_low";}
// Expand a record into dataset x protocol-family rows when the unit setting asks for it.
function unitRows(e){if(SET.unit!=="protocol"||!e.by_protocol||!Object.keys(e.by_protocol).length)return [applyVariant(e)];
  return Object.entries(e.by_protocol).map(([pf,b])=>applyVariant({...e,...b,by_protocol:undefined,tasks:(e.tasks||[]).filter(t=>t.protocol_family===pf),protocol_family:pf,name:`${e.name} · ${pf}`,base_name:e.name,explanation:`${pf} comparisons only. `+(e.explanation||"")}));}
function settingsBar(onChange,keys){keys=keys||Object.keys(SETTINGS_DEF);
  const el=document.createElement("div");el.className="settings";
  const def=k=>SETTINGS_DEF[k].options.find(o=>o[0]===SET[k])[2];
  el.innerHTML=`<p class="sethead">These settings change how the scores are computed. The defaults are the main analysis.${infoIcon('settings')}</p>`+keys.map(k=>`<div class="setrow"><label class="grp">${SETTINGS_DEF[k].label}<select class="sel sm" data-s="${k}">${SETTINGS_DEF[k].options.map(o=>`<option value="${o[0]}" title="${esc(o[2])}"${SET[k]===o[0]?' selected':''}>${o[1]}</option>`).join('')}</select></label><span class="setdef" data-d="${k}">${esc(def(k))}</span></div>`).join('')+`<button type="button" class="reset" ${isDefaultSettings()?'hidden':''}>Restore defaults</button>`;
  const upd=()=>{el.querySelectorAll("[data-d]").forEach(d=>d.textContent=def(d.dataset.d));el.querySelector(".reset").hidden=isDefaultSettings();};
  el.querySelectorAll("select").forEach(s=>s.addEventListener("change",()=>{SET[s.dataset.s]=s.value;settingsSave();upd();onChange();}));
  el.querySelector(".reset").addEventListener("click",()=>{Object.assign(SET,SETTINGS_DEFAULT);settingsSave();el.querySelectorAll("select").forEach(s=>s.value=SET[s.dataset.s]);upd();onChange();});
  return el;}
// one-line definitions shown under a dropdown for its current choice
function bindHelp(select,defs,target){const f=()=>{target.textContent=defs[select.value]||'';};select.addEventListener('change',f);f();}
METRICS.settings={name:"Advanced settings",what:"The scoring method leaves a few choices open. Every benchmark has been scored under each choice, so these controls switch the page between them. A note above the table appears whenever a setting differs from the default.",how:"Score among all models or the top half; include or exclude scores from a model's own paper; score each dataset once or separately for frozen and fine-tuned evaluations; combine seed noise by median or mean; stable or predictive latent-factor model."};
METRICS.general={name:"General ability",what:"The scalar a one-factor leaderboard would give: the model's predicted standardised score averaged over every imagery task, computed from its full capability profile.",how:"mean over all tasks t of λ_tᵀθ_m from the latent-factor fit (ridge 10, K factors), so a model evaluated on few tasks is placed by what its profile predicts elsewhere. 'Independent' uses a fit on evaluations by papers that did not introduce the model; 'all' uses every evaluation. general_obs restricts the mean to the tasks the model was actually evaluated on; mean z is the raw within-comparison z-score mean (the previous ranking).",eq:"Eq. 9"};
METRICS.selfgap={name:"Self-report gap",what:"How much higher the model's general ability comes out when its own paper's evaluations are included. Positive = the introducing paper places it above where other groups do.",how:"general(all evaluations) − general(independent evaluations), from two separate latent-factor fits."};
METRICS.theta={name:"Capability profile θ",what:"The model's position on each latent capability axis. Axes are the principal axes of the task loadings and are not uniquely interpretable (any rotation fits equally well); read them through the datasets that load on them.",how:"θ_m from the latent-factor regression with Cov(θ) = I over models, rotated to the principal axes of Λ. Axis 1 carries most of the shared variance (close to general ability); later axes separate tasks that order models differently. Each axis is described by the datasets with the most positive and most negative loadings and by how much of its loadings domain, sensor, task type or protocol explain.",eq:"Eq. 9"};

// Verdict vocabulary shared by every page: label and one-line meaning.
const VERDICTS={e_reliable:["ev-reliable","Reliable","Score ≥ 0.8 with measured seed noise."],e_moderate:["ev-moderate","Moderate","Score 0.5–0.8 with measured seed noise."],e_weak:["ev-weak","Unreliable","Score below 0.5: model differences are mostly noise."],e_prov_high:["ev-prov-high","Likely reliable","Score ≥ 0.8, but seed noise is estimated, not measured."],e_prov_low:["ev-prov-low","Uncertain","Score below 0.8 with estimated seed noise."],e_spread:["ev-spread","No noise data","Spread is known; seed noise is neither printed nor estimable."],e_few:["ev-few","Too few models","No comparison includes four models."],e_none:["ev-none","No published results","No foundation-model scores found."]};
const range=(lo,hi,d=2)=>lo==null||hi==null?'':` (${Number(lo).toFixed(d)}–${Number(hi).toFixed(d)})`;

document.write('<script src="assets/metric-details.js"><\/script>');
