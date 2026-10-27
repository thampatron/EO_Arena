// Shared chrome and helpers for all pages.
const REPO = "https://github.com/thampatron/EO_Arena";
const PAGES = [["index.html","Explorer"],["map.html","Map"],["tasks.html","Tasks"],["benchmarks.html","Benchmark ranking"],["evidence.html","Evidence map"],["domains.html","Domains"],["sensors.html","Sensors"],["about.html","About"]];
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
  models:{name:"Models",what:"Distinct GeoFMs with a published score on this benchmark.",how:"Count of unique model_id over the benchmark's comparisons, after dropping re-cited numbers (agreement_vs_recitation ≠ original), ablation variants (model_id containing _abl), non-foundation baselines and training from scratch."},
  papers:{name:"Papers",what:"Distinct papers that reported a score on this benchmark. With one paper, the reliability score describes one lab's evaluation and says nothing about whether other labs would separate the models the same way.",how:"Count of unique paper_key over the benchmark's comparisons."},
  tasks_n:{name:"Comparisons",what:"The number of tasks in the sense of the scoring note: one dataset–protocol bundle with at least 4 GeoFMs evaluated the same way.",how:"One comparison = one paper × benchmark id × evaluation protocol × metric × training fraction with ≥ 4 models. The paper is used as the proxy for decoder, split and implementation, which the workbook does not record separately. Comparisons with fewer than 4 models are not scored.",eq:"Sec. 1, 'task'"},
  results:{name:"Reported results",what:"Number of reported score rows behind this benchmark (model × protocol × metric × fraction).",how:"Row count in the workbook's results_long after the exclusions above."},
  spread_pts:{name:"Spread",what:"Observed separation of the models: the standard deviation of GeoFM scores within one comparison, in metric points.",how:"√τ²_obs, where τ²_obs = Var over models of the reported value (ddof = 1), computed per comparison and averaged over the benchmark's comparisons weighted by their number of models. Shown only for metrics printed as percentages or fractions; other units are shown per comparison in the detail.",eq:"Eq. 10"},
  noise_sd:{name:"Seed noise",what:"The run-to-run noise of a single evaluation of one model (σ): seeds, initialisation, finite test set.",how:"Measured: the median over models of the squared SD that the paper reports for each model, from per-seed values listed in the cell (GEO-Bench v2 leaderboard, 5 seeds) or a printed 'mean ± sd' / 'mean (sd)', when ≥ 3 models in the comparison have one. SDs are rescaled to the normalised metric units; a printed ± 0.00 is treated as missing. Plug-in (provisional): the model-weighted σ² of the same dataset under the same protocol family and metric where measured, else the median measured σ² of that protocol family (points-scale metrics only). Shown as √σ² in points.",eq:"Eq. 1, σ²_t"},
  n_reps:{name:"Replicates per value",what:"How many runs each reported value averages. A mean over n runs has noise σ²/n, not σ², so this enters the correction of the observed spread.",how:"Seed-list length when the cell lists seeds (5 for GEO-Bench v2); otherwise the count the paper states in its notes (Prithvi-v2 10, GeoCrossBench 5, EarthShift 5, TESSERA 5, Presto 3, AGBD 3, …); otherwise 3, assumed and flagged. Provisional comparisons use 1 (full σ² subtracted, conservative)."},
  score:{name:"Score",what:"The share of the observed model spread that is repeatable model difference rather than evaluation noise. 1 = every point of spread is real; 0.5 = stable differences equal the noise; 0 = nothing beyond noise. The core metric.",how:"Per comparison: τ² = max(τ²_obs − σ²/n_reps, 0); score = τ²/(τ² + σ²). Per benchmark: the model-count-weighted mean over comparisons with measured noise (directly measured, or carried over from the same dataset/protocol family/metric); if none, over provisional comparisons, and the verdict says so. The 90% interval resamples the models within each comparison with replacement (200 draws), recomputes the weighted mean jointly, and is re-centred on the point estimate because resampling 4–8 models biases the variance down. A σ < 0.1 pt flag marks measured noise so small that EDI is dominated by the denominator; the value is kept, not floored.",eq:"Eq. 6"},
  score_top:{name:"Frontier score",what:"The same score computed only among the leading half of the models in each comparison: can the benchmark still separate the strongest models once weak baselines are set aside? Addresses the saturation of the full score.",how:"Keep the top ⌈n/2⌉ models (at least 4) of each comparison by reported value, recompute τ²_obs on them, then τ² = max(τ²_obs − σ²/n_reps, 0) and score = τ²/(τ² + σ²) with the same σ². Aggregated like the score. Not in the note; added as a diagnostic.",eq:"Eq. 6 on a subset"},
  edi:{name:"EDI",what:"Effective discriminative information: how many times larger the stable between-model variance is than the noise of one evaluation. Unbounded; the score is EDI/(1 + EDI).",how:"Per benchmark, derived from the aggregated score: EDI = score/(1 − score). ∞ when the measured noise is zero. Use it to rank among benchmarks whose scores all sit near 1.",eq:"Eq. 4"},
  unexplained_share:{name:"Dataset-specific signal",what:"Share of the stable model differences on this benchmark that the shared capability factors do not explain. High = the benchmark ranks models in its own way; low = it mostly repeats what other benchmarks measure. A diagnostic, not a penalty.",how:"From the latent-factor regression y_mt = μ_t + λ_tᵀθ_m + η_mt fitted by alternating ridge least squares (ridge 10, K = 3) on all imagery comparisons after standardising each to unit variance. Ψ_tt = max(residual variance × τ²_obs − σ²/n_reps, 0); share = min(Ψ_tt/τ², 1), averaged over comparisons weighted by models.",eq:"Eq. 5"},
  info_share:{name:"Info share",what:"Redundancy-adjusted contribution: how much of the information the whole evidence base gives about shared GeoFM capabilities this benchmark adds, with credit split among near-duplicate benchmarks.",how:"Shapley share (300 random orderings) of V(A) = log det(I + Λ_Aᵀ C_A⁻¹ Λ_A) over datasets, with Λ the fitted loadings and C the diagonal residual variance (floored at 0.05) in standardised units; normalised to sum to 1 over datasets.",eq:"Eq. 7–8"},
  self_share:{name:"Self-reported",what:"Share of scores that come from the paper that introduced the model.",how:"Mean of the workbook's is_self_reported flag over the cells in the benchmark's comparisons, weighted by models. Each model release counts as its own team; a lab's later paper counts as independent for its earlier models. Not used in the score."},
  suites:{name:"In suites",what:"Published benchmark suites that already include this dataset (PANGAEA, GEO-Bench, GEO-Bench-2, Copernicus-Bench, …). A dataset in several suites is one reviewers will recognise.",how:"From the EOArena inventory's audit of suite membership (data/datasets.json, benchmark_suites). Hover the cell for the full list. Datasets not in the inventory show –."},
  verdict:{name:"Verdict",what:"A label summarising the score and whether the noise was measured or plugged in.",how:"Reliable: score ≥ 0.8 with measured noise. Moderate: 0.5–0.8 measured. Weak / saturated: < 0.5 measured. Provisional (high/low): ≥ 0.8 / < 0.8 with plug-in noise. Spread only: no noise estimate. Under 4 models: no comparison large enough to score. The ranking orders by verdict, then number of papers, then score."},
  r2_shared:{name:"Shared-factor R²",what:"Share of the observed within-comparison variance reproduced by the K shared capability factors.",how:"1 − residual variance / observed variance per comparison from the latent-factor fit, in standardised units, model-weighted over comparisons."},
  protocol:{name:"Protocol family",what:"Frozen (linear probe, kNN, frozen encoder + decoder) or fine-tuned (full or partial), the main split in how a GeoFM is adapted.",how:"evaluation_protocol mapped to a family: FT/PFT → fine-tuned; frozen_dec/LP/kNN/frozen/frozen_best/PE/MLP → frozen; others kept as named."},
};
function infoIcon(key){const m=METRICS[key];if(!m)return '';return `<button type="button" class="info" data-m="${key}" aria-label="About ${esc(m.name)}">i</button>`;}
function infoPop(key,anchor){
  document.querySelectorAll('.pop').forEach(p=>p.remove());
  const m=METRICS[key];if(!m)return;
  const pop=document.createElement('div');pop.className='pop';pop.setAttribute('role','dialog');
  pop.innerHTML=`<div class="pop-h"><b>${esc(m.name)}</b>${m.eq?`<span class="pop-eq">${esc(m.eq)}</span>`:''}<button type="button" class="pop-x" aria-label="Close">×</button></div><p>${esc(m.what)}</p><p class="pop-how"><b>How it is computed.</b> ${esc(m.how)}</p><p class="pop-src">Definitions follow S. Wang, <i>GeoFM Benchmark Scoring</i> (Oct 2026). Code: <code>scripts/geofm_scoring.py</code>, <code>scripts/build_evidence.py</code>.</p>`;
  document.body.append(pop);
  const r=anchor.getBoundingClientRect();const w=Math.min(380,innerWidth-24);pop.style.width=w+'px';
  pop.style.left=Math.max(12,Math.min(r.left+scrollX-8,scrollX+innerWidth-w-12))+'px';pop.style.top=(r.bottom+scrollY+8)+'px';
  pop.querySelector('.pop-x').addEventListener('click',()=>pop.remove());
}
document.addEventListener('click',e=>{const b=e.target.closest('button.info[data-m]');if(b){e.stopPropagation();infoPop(b.dataset.m,b);return;}if(!e.target.closest('.pop'))document.querySelectorAll('.pop').forEach(p=>p.remove());});
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.pop').forEach(p=>p.remove());});

// ---------------------------------------------------------------------------------------------------------------------
// Analysis settings shared by the evidence pages: which variant of the scoring to show. Stored in the URL (so a view
// can be shared) and in localStorage (so it follows the reader between pages).
const SETTINGS_DEF = {
  noise:{label:"Combine seed noise across models by",options:[["median","median (robust)"],["mean","mean"]],help:"How the per-model seed variances in a comparison are combined into one σ². Median is robust to one unstable run; mean is the textbook pooled estimate."},
  self:{label:"Scores from a model's own paper",options:[["all","keep"],["independent","drop"]],help:"Dropped = scores reported by the paper that introduced the model are removed before anything is computed; a comparison must keep at least 4 models."},
  headline:{label:"Score computed among",options:[["score","all models"],["score_top","the top half of models only"]],help:"Which score is used for the verdict, the rank and the Explorer panel. Frontier = computed among the top half of the models in each comparison."},
  unit:{label:"One row per",options:[["dataset","dataset"],["protocol","dataset × frozen/fine-tuned"]],help:"Score each dataset once over all its comparisons, or separately for frozen and fine-tuned evaluations (the note's definition of a task)."},
  ridge:{label:"Latent-factor fit",options:[["10","stable (ridge 10)"],["3","predictive (ridge 3)"]],help:"Regularisation of the latent-factor regression behind dataset-specific signal and info share. Ridge 10 gives a task geometry stable under bootstrap (0.66); ridge 3 predicts held-out cells better but its geometry is not reproducible (0.3-0.4)."},
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
function settingsSummary(){return Object.keys(SETTINGS_DEF).filter(k=>SET[k]!==SETTINGS_DEFAULT[k]).map(k=>`${SETTINGS_DEF[k].label}: ${SETTINGS_DEF[k].options.find(o=>o[0]===SET[k])[1]}`).join(" · ");}
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
  const el=document.createElement("div");el.className="settings";el.innerHTML=`<span class="k">Analysis settings${infoIcon('settings')}</span>`+keys.map(k=>`<label class="grp">${SETTINGS_DEF[k].label}<select class="sel sm" data-s="${k}" title="${esc(SETTINGS_DEF[k].help)}">${SETTINGS_DEF[k].options.map(o=>`<option value="${o[0]}"${SET[k]===o[0]?' selected':''}>${o[1]}</option>`).join('')}</select></label>`).join('')+`<button type="button" class="reset" ${isDefaultSettings()?'hidden':''}>Reset</button>`;
  el.querySelectorAll("select").forEach(s=>s.addEventListener("change",()=>{SET[s.dataset.s]=s.value;settingsSave();el.querySelector(".reset").hidden=isDefaultSettings();onChange();}));
  el.querySelector(".reset").addEventListener("click",()=>{Object.assign(SET,SETTINGS_DEFAULT);settingsSave();el.querySelectorAll("select").forEach(s=>s.value=SET[s.dataset.s]);el.querySelector(".reset").hidden=true;onChange();});
  return el;}
METRICS.settings={name:"Analysis settings",what:"The scoring note leaves a few choices open. Every dataset is scored under each of them, and these controls switch the whole page between the variants. The defaults are the main analysis; the choice follows you between pages and is written into the URL.",how:"σ²: median (default) or mean of the per-model seed variances within a comparison. Self-reported: keep all scores, or drop those from the paper that introduced the model before computing anything (comparisons that fall below 4 models are dropped). Headline: the full-comparison score (Eq. 6) or the frontier score (leading half of each comparison) drives verdicts and ranks. Unit: one score per dataset, or one per dataset × protocol family (frozen / fine-tuned), the note's own definition of a task. Latent fit: ridge 10 (main; stable geometry) or ridge 3 (better held-out prediction, unstable geometry) for dataset-specific signal and info share."};
METRICS.general={name:"General ability",what:"The scalar a one-factor leaderboard would give: the model's predicted standardised score averaged over every imagery task, computed from its full capability profile.",how:"mean over all tasks t of λ_tᵀθ_m from the latent-factor fit (ridge 10, K factors), so a model evaluated on few tasks is placed by what its profile predicts elsewhere. 'Independent' uses a fit on evaluations by papers that did not introduce the model; 'all' uses every evaluation. general_obs restricts the mean to the tasks the model was actually evaluated on; mean z is the raw within-comparison z-score mean (the previous ranking).",eq:"Eq. 9"};
METRICS.selfgap={name:"Self-report gap",what:"How much higher the model's general ability comes out when its own paper's evaluations are included. Positive = the introducing paper places it above where other groups do.",how:"general(all evaluations) − general(independent evaluations), from two separate latent-factor fits."};
METRICS.theta={name:"Capability profile θ",what:"The model's position on each latent capability axis. Axes are the principal axes of the task loadings and are not uniquely interpretable (any rotation fits equally well); read them through the datasets that load on them.",how:"θ_m from the latent-factor regression with Cov(θ) = I over models, rotated to the principal axes of Λ. Axis 1 carries most of the shared variance (close to general ability); later axes separate tasks that order models differently. Each axis is described by the datasets with the most positive and most negative loadings and by how much of its loadings domain, sensor, task type or protocol explain.",eq:"Eq. 9"};
