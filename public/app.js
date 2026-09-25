const $ = id => document.getElementById(id);
let catalog, activeCase, reference = 'late_bridge', report = null, selected = null, busy = false, briefText = '';
let pinnedReport = null;
let bundleBusy = false;
let comparisonBusy = false;
let importedContract = null, importedMeta = null, customPlan = null, customPlanSource = null;
let candidateSource = '', candidateProvenance = 'custom candidate', customPlanProvenance = null;
const fields = {name: 'plan-name', migration: 'migration', read: 'read', write: 'write', insert: 'insert'};
const labels = {compatibility: 'Old worker alive', mixed_versions: 'Mixed versions', rollback: 'Rollback reads', new_records: 'New records', interleaving: 'Write order', in_flight: 'Before migration', migration_window: 'Migration windows'};
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty = value => JSON.stringify(value, null, 2);
const currentPlan = () => Object.fromEntries(Object.entries(fields).map(([key, id]) => [key, $(id).value]));
const emptyPlan = () => Object.fromEntries(Object.keys(fields).map(key => [key, '']));
const candidateReady = () => Object.values(currentPlan()).every(value => value.trim());
const fileSlug = value => String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'contract';

function notify(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(notify.timer); notify.timer = setTimeout(() => $('toast').hidden = true, 5000); }
function download(name, content, type='application/json') { const url = URL.createObjectURL(new Blob([content], {type})); const a = document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); }
function updateModeControls() {
  const custom=activeCase?.id==='custom';
  $('plan-options').hidden=custom; $('custom-plan-intro').hidden=!custom; $('save-contract').hidden=!custom;
  document.querySelectorAll('[data-plan]').forEach(button=>button.disabled=busy||custom);
  $('try-cross-record').disabled=busy||custom;
  $('run').disabled=busy||!activeCase||(custom&&!candidateReady());
  $('quick-run').disabled=$('run').disabled;
  $('save-plan').disabled=busy||!activeCase||(custom&&!candidateReady());
  $('try-warehouse').disabled=busy;
}
function setBusy(value, label='Executing SQL rehearsals…') {
  busy=value;
  for (const node of document.querySelectorAll('.candidate-panel button,.candidate-panel textarea,.candidate-panel input,#case,#import-contract')) node.disabled=value;
  $('try-warehouse').disabled=value;
  $('quick-run').disabled=value;
  $('run').innerHTML=value?`<span>${escape(label)}</span><span>◌</span>`:'<span>Run release rehearsal</span><span>↗</span>';
  if(!value){updateModeControls();renderComparison();}
}

function invalidate() {
  report=null; selected=null;
  $('status-badge').textContent='NOT RUN'; $('status-badge').className='status-badge';
  $('verdict-title').textContent='Ready to rehearse.';
  $('verdict-description').textContent='This candidate has not been executed. Run it to produce fresh evidence.';
  $('baseline-count').innerHTML='—<small> / —</small>'; $('probe-count').innerHTML='—<small> / —</small>';
  $('baseline-count').className=''; $('probe-count').className='';
  $('baseline-note').textContent='Not run'; $('probe-note').textContent='Not run';
  $('coverage').replaceChildren(); $('runtime').textContent='—'; $('hashes').textContent='';
  $('matrix').innerHTML='<p class="empty">Run this candidate to inspect its evidence.</p>';
  $('trace').replaceChildren(); $('trace-title').textContent='Nothing inferred. Everything replayed.'; $('trace-id').textContent=''; $('trace-payload').textContent='';
  $('trace-label').textContent='REPLAY';
  $('window-map').hidden=true; $('window-stages').replaceChildren();
  $('finding').innerHTML='<span class="finding-icon">↳</span><div><h3>Evidence, before assurance.</h3><p>Every result comes from executed SQL and an independent record of acknowledged writes.</p></div>';
  $('export').disabled=true; $('export-review').disabled=true; $('export-repro').disabled=true; $('export-bundle').disabled=true; $('brief').disabled=true;
  renderComparison();
}
function renderComparison() {
  const tools=$('comparison-tools'), panel=$('comparison-panel');
  const timeline=$('comparison-timeline');
  timeline.hidden=true;
  $('export-comparison').hidden=true;
  tools.hidden=!report&&!pinnedReport;
  $('pin-baseline').disabled=!report||busy;
  $('clear-baseline').hidden=!pinnedReport;
  panel.hidden=!pinnedReport;
  if(!pinnedReport)return;
  const pinnedName=pinnedReport.plan.name;
  const comparing=report&&report!==pinnedReport;
  $('comparison-title').textContent=comparing?`${pinnedName} → ${report.plan.name}`:`Pinned: ${pinnedName}`;
  const baseHash=pinnedReport.plan_hash.slice(0,10);
  if(!comparing) {
    $('comparison-detail').textContent=`Baseline ${pinnedReport.passed}/${pinnedReport.total} · plan ${baseHash}. Run another candidate to compare.`;
    $('comparison-metrics').replaceChildren();
    $('comparison-changes').replaceChildren();
    return;
  }
  if(pinnedReport.contract_hash!==report.contract_hash||pinnedReport.engine_sha256!==report.engine_sha256||pinnedReport.suite_hash!==report.suite_hash) {
    $('comparison-detail').textContent='These reports use different contracts or evaluator versions. Pin the current result to start a comparable baseline.';
    $('comparison-metrics').replaceChildren();
    $('comparison-changes').replaceChildren();
    return;
  }
  const sameMigration=pinnedReport.plan.migration===report.plan.migration;
  const before=new Map(pinnedReport.results.filter(item=>sameMigration||item.category!=='migration_window').map(item=>[item.id,item]));
  let paired=0, resolved=0, regressed=0;
  const firstRegression=[];
  for(const item of report.results) {
    if(!sameMigration&&item.category==='migration_window')continue;
    const old=before.get(item.id);
    if(!old||old.payload!==item.payload||JSON.stringify(old.actions)!==JSON.stringify(item.actions))continue;
    paired++;
    if(!old.passed&&item.passed)resolved++;
    if(old.passed&&!item.passed){regressed++;if(firstRegression.length<3)firstRegression.push(item);}
  }
  const oldWindows=pinnedReport.categories.find(item=>item.id==='migration_window');
  const newWindows=report.categories.find(item=>item.id==='migration_window');
  $('comparison-detail').textContent=sameMigration
    ?`Same migration and contract · paired ${paired} probes. Plans ${baseHash} → ${report.plan_hash.slice(0,10)}.`
    :`Same contract, different migration. Paired ${paired} completed-rollout probes; statement-boundary probes cannot be paired across different SQL sequences. Plans ${baseHash} → ${report.plan_hash.slice(0,10)}.`;
  $('comparison-metrics').innerHTML=`<div><span>PAIRED ${sameMigration?'':'NON-WINDOW '}PROBES RESOLVED</span><strong>${resolved}</strong></div><div><span>PAIRED ${sameMigration?'':'NON-WINDOW '}PROBES REGRESSED</span><strong class="${regressed?'red':''}">${regressed}</strong></div><div><span>MIGRATION WINDOW FAILURES</span><strong>${oldWindows.total-oldWindows.passed} → ${newWindows.total-newWindows.passed}</strong><small>${oldWindows.total} → ${newWindows.total} boundary probes, ${sameMigration?'paired':'evaluated separately'}</small></div>`;
  const firstWindow=report.results.find(item=>item.category==='migration_window'&&!item.passed);
  const links=firstRegression.map(item=>`<button type="button" data-comparison-probe="${escape(item.id)}">New regression: ${escape(item.title)} ↗</button>`);
  if(firstWindow&&!firstRegression.some(item=>item.id===firstWindow.id))links.push(`<button type="button" data-comparison-probe="${escape(firstWindow.id)}">Candidate window witness: ${escape(firstWindow.title)} ↗</button>`);
  $('comparison-changes').innerHTML=links.length?`<span>INSPECT THE CANDIDATE REPLAY</span>${links.join('')}`:'<span>No newly failing paired probe or candidate window witness.</span>';
  $('comparison-changes').querySelectorAll('[data-comparison-probe]').forEach(button=>button.addEventListener('click',()=>{
    const probe=report.results.find(item=>item.id===button.dataset.comparisonProbe);
    if(probe){renderTrace(probe);$('trace-title').scrollIntoView({behavior:'smooth',block:'center'});}
  }));
  $('comparison-timeline-grid').innerHTML=boundaryTimeline(pinnedReport,'PINNED BASELINE')+boundaryTimeline(report,'CURRENT CANDIDATE');
  timeline.hidden=false;
  $('export-comparison').hidden=false;
  $('export-comparison').disabled=busy||comparisonBusy;
}
function boundaryTimeline(measured, label) {
  const windows=measured.results.filter(item=>item.category==='migration_window');
  const boundaries=new Map(), statements=new Map();
  for(const probe of windows) {
    const match=/^window_(write|insert)_after_(\d+)-/.exec(probe.id);
    if(!match)continue;
    const boundary=Number(match[2]);
    if(!boundaries.has(boundary))boundaries.set(boundary,{write:[],insert:[]});
    boundaries.get(boundary)[match[1]].push(probe);
    for(const event of probe.trace) {
      const sqlStep=/^migration\.statement\.(\d+)$/.exec(event.action);
      if(sqlStep&&!statements.has(Number(sqlStep[1]))&&event.sql)statements.set(Number(sqlStep[1]),event.sql);
    }
  }
  if(!boundaries.size)return `<div class="timeline-plan"><b>${escape(label)}</b><p>No statement-boundary probes retained.</p></div>`;
  const last=Math.max(...boundaries.keys());
  const rows=[];
  for(let step=0;step<=last;step++) {
    if(step>0) {
      const sql=statements.get(step-1);
      rows.push(`<details class="timeline-sql"><summary><span>SQL ${step}</span><code>${escape(sql?.replace(/\s+/g,' ').trim()||'Statement not observed in retained traces')}</code></summary>${sql?`<pre>${escape(sql)}</pre>`:''}</details>`);
    }
    const kinds=boundaries.get(step);
    if(!kinds)continue;
    const count=kind=>`${kinds[kind].filter(item=>item.passed).length}/${kinds[kind].length}`;
    const failed=[...kinds.write,...kinds.insert].some(item=>!item.passed);
    rows.push(`<div class="timeline-boundary ${failed?'fail':'pass'}"><span>${step===0?'BEFORE SQL':`AFTER SQL ${step}`}</span><strong>Update ${count('write')} · Insert ${count('insert')}</strong></div>`);
  }
  return `<div class="timeline-plan"><b>${escape(label)} · ${escape(measured.plan.name)}</b><small>${measured.plan_hash.slice(0,10)} · ${last} SQL statements</small>${rows.join('')}</div>`;
}
function setPlan(plan, source, provenance='custom candidate') {
  Object.entries(fields).forEach(([key,id])=>$(id).value=plan[key]);
  candidateSource=source;
  candidateProvenance=provenance;
  $('source-label').textContent=source;
  document.querySelectorAll('[data-plan]').forEach(button=>{ const chosen=button.dataset.plan===reference; button.classList.toggle('selected',chosen); button.setAttribute('aria-pressed',String(chosen)); });
  invalidate();
}
function chooseCase() {
  if(activeCase?.id==='custom'&&$('case').value!=='custom') {customPlan=currentPlan();customPlanSource=candidateSource;customPlanProvenance=candidateProvenance;}
  const custom=$('case').value==='custom';
  activeCase=custom?{id:'custom',...importedContract}:catalog.cases.find(c=>c.id===$('case').value);
  reference=custom?null:'late_bridge';
  $('case-description').textContent=activeCase.summary;
  $('old-contract').textContent=pretty(activeCase.old);
  $('variant-count').textContent=`${custom?activeCase.payloads.length:4} INPUT VARIANTS`;
  setPlan(custom?(customPlan||emptyPlan()):activeCase.plans[reference],
          custom?(customPlanSource||'Imported contract · candidate not yet executed'):'Editable reference · not AI generated',
          custom?(customPlanProvenance||'custom candidate'):'prewritten reference');
  updateModeControls();
}

async function run() {
  if(busy) return;
  const plan=currentPlan(), caseId=activeCase.id;
  const request={case:caseId,plan};
  if(caseId==='custom')request.contract=importedContract;
  setBusy(true); invalidate(); $('status-badge').textContent='RUNNING';
  try {
    const body=JSON.stringify(request);
    if(new Blob([body]).size>65536)throw Error('Contract and plan exceed the 64 KiB hosted request limit. Use the local CLI.');
    const response=await fetch('/api/rehearse',{method:'POST',headers:{'Content-Type':'application/json'},body});
    const data=await response.json(); if(!response.ok) throw Error(data.error||'Rehearsal failed');
    report=data; renderReport();
  } catch(error) { invalidate(); $('status-badge').textContent='ERROR'; $('verdict-title').textContent='No result produced.'; $('verdict-description').textContent=error.message; notify(error.message); }
  finally {setBusy(false);}
}
function renderReport() {
  const passed=report.status==='pass';
  const complete=report.categories.filter(c=>c.id!=='migration_window');
  const completeTotal=complete.reduce((n,c)=>n+c.total,0);
  const completePassed=complete.reduce((n,c)=>n+c.passed,0);
  const windows=report.categories.find(c=>c.id==='migration_window');
  const provenance=reference==='cross_record'?'prewritten negative control':reference?'prewritten reference':candidateProvenance;
  $('source-label').textContent=`Executed ${provenance} · ${report.plan_hash.slice(0,10)}`;
  $('status-badge').textContent=passed?'SUITE PASSED':'BLOCKED'; $('status-badge').className=`status-badge ${report.status}`;
  $('verdict-title').textContent=passed?'The handover holds.':'The handover breaks.';
  $('verdict-description').textContent=passed?'Both versions observed the expected data in every tested schedule and migration window. Keep the compatibility path through the rollback window.':completePassed===completeTotal&&windows?.passed<windows?.total?`All ${completeTotal} completed-rollout probes passed. ${windows.total-windows.passed} migration-window probes failed while old workers were still active.`:`${report.failed} probes failed. ${report.baseline.passed===report.baseline.total?'A green new-version baseline does not establish that old and new workers can safely share the data.':'The new-version baseline also fails; this candidate does not meet the required target-column contract.'}`;
  $('baseline-count').innerHTML=`${report.baseline.passed}<small> / ${report.baseline.total}</small>`;
  $('baseline-count').className=report.baseline.passed===report.baseline.total?'green':'red';
  $('baseline-note').textContent=report.baseline.passed===report.baseline.total?'✓ Same-version checks pass':'× Same-version failures';
  $('probe-count').innerHTML=`${report.passed}<small> / ${report.total}</small>`; $('probe-count').className=passed?'green':'red';
  $('probe-note').textContent=passed?'✓ All tested schedules pass':`× ${report.failed} failed probes`;
  $('runtime').textContent=`${report.duration_ms} ms engine time`;
  $('coverage').innerHTML=report.categories.map(c=>`<div class="coverage-row"><span>${escape(labels[c.id])}</span><div class="meter" aria-label="${c.passed} of ${c.total} passed">${Array.from({length:c.total},(_,i)=>`<i class="${i<c.passed?'good':'bad'}"></i>`).join('')}</div><span>${c.passed}/${c.total}</span></div>`).join('');
  const witness=report.witness;
  const failedRead=witness?.trace.find(step=>step.status==='fail'&&step.expected&&step.actual);
  const rowId=failedRead&&[...new Set([...Object.keys(failedRead.expected),...Object.keys(failedRead.actual)])].find(id=>failedRead.expected[id]!==failedRead.actual[id]);
  const value=value=>value===undefined?'(missing row)':JSON.stringify(value);
  const gap=rowId===undefined?'':`<p class="witness-gap">Row ${escape(rowId)} · ledger expected <strong>${escape(value(failedRead.expected[rowId]))}</strong>; ${escape(failedRead.action)} observed <strong>${escape(value(failedRead.actual[rowId]))}</strong>.</p>`;
  $('finding').innerHTML=`<span class="finding-icon">${passed?'✓':'↳'}</span><div><h3>${passed?'Passing evidence, with a boundary.':witness.failure.kind==='data_mismatch'?'The SQL worked. The data disagreed.':['adapter_contract','target_contract','target_mismatch'].includes(witness.failure.kind)?'The target contract is unmet.':'A real query fails during handover.'}</h3><p>${passed?`${report.total} probes passed on this SQLite contract. This does not certify untested workloads or another database engine.`:escape(witness.failure.message)}</p>${gap}</div>`;
  $('export').disabled=false; $('export-review').disabled=!report.review_markdown; $('export-repro').disabled=!report.reproduction_python; $('export-bundle').disabled=bundleBusy; $('brief').disabled=false;
  $('hashes').textContent=`Plan SHA-256: ${report.plan_hash} · Contract SHA-256: ${report.contract_hash} · Suite SHA-256: ${report.suite_hash}`;
  renderComparison();
  renderWindowMap(); renderMatrix(); renderTrace(witness || report.results.find(r=>r.id==='new_to_old-0'));
}
function renderWindowMap() {
  const grouped=new Map();
  for(const probe of report.results.filter(item=>item.category==='migration_window')) {
    const match=/^window_(write|insert)_after_(\d+)-/.exec(probe.id);
    if(!match)continue;
    const step=Number(match[2]);
    if(!grouped.has(step))grouped.set(step,{write:[],insert:[]});
    grouped.get(step)[match[1]].push(probe);
  }
  if(!grouped.size){$('window-map').hidden=true;return;}
  const last=Math.max(...grouped.keys());
  const earliest=[...grouped].find(([,kinds])=>[...kinds.write,...kinds.insert].some(probe=>!probe.passed));
  const firstFailure=earliest&&[...earliest[1].write,...earliest[1].insert].find(probe=>!probe.passed);
  const brokenAction=firstFailure?.failure?.action;
  const windowFinding=brokenAction==='old.read'?'An old reader breaks before the migration finishes.':brokenAction==='new.read'?'An acknowledged old operation is missing from the final new read.':brokenAction?.startsWith('old.')?'An old worker operation fails during the migration.':'Inspect the failing replay for the broken step.';
  $('window-summary').textContent=earliest
    ?`First observed gap: after statement ${earliest[0]} of ${last}. ${windowFinding}`
    :`Old writes, inserts, and reads stayed consistent in ${report.categories.find(item=>item.id==='migration_window')?.total||0} tested migration windows.`;
  $('window-stages').innerHTML=[...grouped].map(([step,kinds])=>`<div class="window-stage"><b>${step===0?'BEFORE SQL':`AFTER ${step}/${last}`}</b>${['write','insert'].map(kind=>{
    const probes=kinds[kind], failures=probes.filter(probe=>!probe.passed), picked=failures[0]||probes[0];
    return `<button type="button" class="${failures.length?'fail':''}" data-window-probe="${picked.id}" aria-label="${step===0?'Before migration':`After statement ${step} of ${last}`}; old ${kind}; ${probes.length-failures.length} of ${probes.length} passed"><span>Old ${kind==='write'?'update':'insert'}</span><span>${probes.length-failures.length}/${probes.length}</span></button>`;
  }).join('')}</div>`).join('');
  $('window-stages').querySelectorAll('[data-window-probe]').forEach(button=>button.addEventListener('click',()=>{
    renderTrace(report.results.find(probe=>probe.id===button.dataset.windowProbe));
    $('trace-title').scrollIntoView({behavior:'smooth',block:'center'});
  }));
  $('window-map').hidden=false;
}
function renderMatrix() {
  if(!report) return;
  const only=$('failures-only').checked;
  const groups=new Map();
  for(const r of report.results) {const key=r.id.slice(0,r.id.lastIndexOf('-')); if(!groups.has(key))groups.set(key,[]); groups.get(key).push(r);}
  $('matrix').innerHTML=[...groups.values()].filter(group=>!only||group.some(r=>!r.passed)).map(group=>`<div class="matrix-row"><span>${escape(group[0].title)}</span><div class="probe-group">${group.map((r,i)=>`<button class="probe ${r.passed?'':'fail'} ${selected===r.id?'chosen':''}" data-probe="${r.id}" title="${escape(r.payload||'(empty string)')} — ${r.passed?'pass':'fail'}" aria-label="${escape(r.title)}; input ${i+1}; ${r.passed?'passed':'failed'}">${r.passed?'✓':'×'}</button>`).join('')}</div></div>`).join('') || '<p class="empty">No failures in this rehearsal.</p>';
  $('matrix').querySelectorAll('[data-probe]').forEach(b=>b.addEventListener('click',()=>renderTrace(report.results.find(r=>r.id===b.dataset.probe))));
}
function renderTrace(probe) {
  if(!probe)return; selected=probe.id;
  $('trace-label').textContent=report.witness?.id===probe.id?'SHORTEST OBSERVED FAILURE':'EXECUTED REPLAY';
  $('trace-id').textContent=probe.passed?'PASS':'FAIL'; $('trace-title').textContent=probe.title;
  const seededWrite=probe.actions?.some(action=>action.endsWith('.write'));
  const pathNote=probe.write_targets?` · write IDs ${probe.write_targets.join(' → ')} · ${probe.cross_record_paths_tested.length} cross-record paths checked`:'';
  const rowNote=seededWrite?` · ${probe.passed?'Shown':'Failed'} row ID ${probe.seed_id} · ${probe.seed_ids_tested.length}/${activeCase.seed.length} seeded IDs checked${pathNote}`:'';
  const inserted=probe.actions?.some(action=>action.endsWith('.insert'));
  const insertNote=inserted?` · ${probe.passed?'Shown':'Failed'} inserted ID ${probe.insert_id} · checked IDs ${probe.insert_ids_tested.join(', ')}`:'';
  $('trace-payload').textContent=`Input: ${JSON.stringify(probe.payload)}${rowNote}${insertNote}`;
  $('trace').innerHTML=probe.trace.map(event=>{
    const role=event.connection?`<span class="connection-role">${escape(String(event.connection).toUpperCase())} CONNECTION</span>`:'';
    return `<div class="trace-step ${event.status}"><h4><span>${escape(event.action)}</span>${role}</h4><p>${escape(event.detail||'Executed.')}</p><details><summary>Executed SQL${event.params?' & inputs':''}</summary><pre>${escape(event.sql)}${event.params?'\n\n'+escape(pretty(event.params)):''}</pre></details>${event.status==='fail'&&event.actual?`<div class="comparison"><div class="expected">EXPECTED ${escape(pretty(event.expected))}</div><div class="actual">OBSERVED ${escape(pretty(event.actual))}</div></div>`:''}</div>`;
  }).join('');
  document.querySelectorAll('[data-probe]').forEach(b=>b.classList.toggle('chosen',b.dataset.probe===selected));
}
async function showBob() {
  if(activeCase?.id==='custom') {
    if(!candidateReady()||!report) {
      briefText='Import or enter a five-field candidate plan and run a fresh rehearsal before preparing the Bob repair task. The imported contract remains available in this browser session.';
      $('bob-task').value=briefText; $('download-brief').disabled=true; $('bob-dialog').showModal(); return;
    }
    briefText=`Repair this imported SQLite contract in IBM Bob. First call inspect_imported_contract with the contract object below. Call rehearse_candidate with case="custom", this same complete contract object, and your five candidate SQL fields on every attempt. Preserve the fixed old adapter, seed data, and evaluator. Keep old reads and writes correct between completed migration statements. Save your own final plan to work/bob-candidate.json and retain Bob's actual tool calls, task summary, failed attempts and screenshots. Any browser verdict is deterministic evidence, not proof Bob did this work. Use a local Bob session for private schemas. Report measured coverage and untested boundaries.\n\n`+pretty({contract:importedContract,contract_hash:importedMeta?.contract_hash,candidate:currentPlan(),plan_hash:report?.plan_hash||null,shortest_observed_witness:report?.witness||null});
    $('bob-task').value=briefText; $('download-brief').disabled=false; $('bob-dialog').showModal(); return;
  }
  $('download-brief').disabled=false;
  const intro=`Inspect this Cutover project and repair the ${activeCase?.id||'parcel'} rollout. Use inspect_release and rehearse_candidate through the Cutover MCP server. Preserve the fixed old contract and the evaluator. Save your candidate to work/bob-candidate.json. Explain each change and retain your actual Bob task summary and screenshots. Do not claim that prewritten reference solutions are your work.\n\n`;
  if(report) {
    briefText=intro+pretty({case:report.case,plan_hash:report.plan_hash,candidate:report.plan,shortest_observed_witness:report.witness,constraints:['Preserve old/new updates and inserts.','Application rollback must preserve new-version writes.','Protect old writes and reads at every migration statement boundary.','Do not change the old adapter, oracle, seeds or suite to make a plan pass.',`Rerun all ${report.total} probes, then report coverage limits.`]});
  } else briefText=intro+'Begin with the late-bridge candidate. The task is to produce an evidence-backed repair, not to generate a risk score.';
  $('bob-task').value=briefText; $('bob-dialog').showModal();
}

$('run').addEventListener('click',run);
$('pin-baseline').addEventListener('click',()=>{if(!report||busy)return;pinnedReport=report;renderComparison();notify('Baseline pinned in this browser tab. Run another candidate to compare.');});
$('clear-baseline').addEventListener('click',()=>{pinnedReport=null;renderComparison();notify('Comparison baseline cleared.');});
$('quick-run').addEventListener('click',async()=>{
  if(busy||$('run').disabled)return;
  await run();
  $('verdict-title').closest('.result-panel').scrollIntoView({behavior:'smooth',block:'start'});
});
$('case').addEventListener('change',chooseCase);
document.querySelectorAll('[data-plan]').forEach(button=>button.addEventListener('click',()=>{if(busy||activeCase?.id==='custom')return;reference=button.dataset.plan;setPlan(activeCase.plans[reference],'Editable reference · not AI generated');}));
$('try-cross-record').addEventListener('click',()=>{if(busy||activeCase?.id==='custom')return;reference='cross_record';setPlan(activeCase.plans.cross_record,'Prewritten negative control · not AI generated');run();});
Object.values(fields).forEach(id=>$(id).addEventListener('input',()=>{reference=null;candidateSource='Custom candidate · not yet executed';candidateProvenance='custom candidate';$('source-label').textContent=candidateSource;document.querySelectorAll('[data-plan]').forEach(b=>{b.classList.remove('selected');b.setAttribute('aria-pressed','false');});invalidate();updateModeControls();}));
$('failures-only').addEventListener('change',renderMatrix);
$('brief').addEventListener('click',showBob); $('bob-nav').addEventListener('click',showBob);
$('export-bundle').addEventListener('click',async()=>{
  if(!report||bundleBusy)return;
  const snapshot=report, button=$('export-bundle');
  const request={case:snapshot.case,plan:snapshot.plan};
  if(snapshot.case==='custom')request.contract=importedContract;
  bundleBusy=true; button.disabled=true; button.textContent='Preparing review packet…';
  try {
    const body=JSON.stringify(request);
    if(new Blob([body]).size>65536)throw Error('Contract and plan exceed the 64 KiB hosted request limit. Use the local CLI.');
    const response=await fetch('/api/bundle',{method:'POST',headers:{'Content-Type':'application/json'},body});
    if(!response.ok){const data=await response.json();throw Error(data.error||'Review packet failed.');}
    if(response.headers.get('Content-Type')!=='application/zip'||
       response.headers.get('X-Cutover-Plan-SHA256')!==snapshot.plan_hash||
       response.headers.get('X-Cutover-Contract-SHA256')!==snapshot.contract_hash||
       response.headers.get('X-Cutover-Status')!==snapshot.status||
       response.headers.get('X-Cutover-Coverage')!==`${snapshot.passed}/${snapshot.total}`)
      throw Error('The new rehearsal differs from the displayed result. Run the candidate again before exporting.');
    const packet=await response.blob();
    if(report!==snapshot)throw Error('The displayed candidate changed. Run it again before exporting.');
    download(`cutover-${snapshot.case}-${snapshot.plan_hash.slice(0,10)}-review.zip`,packet,'application/zip');
    notify('Review packet downloaded from a fresh server rehearsal.');
  }catch(error){notify(error.message);}
  finally{bundleBusy=false;button.textContent='Download review packet ↓';button.disabled=!report;}
});
$('export-comparison').addEventListener('click',async()=>{
  if(!report||!pinnedReport||busy||comparisonBusy)return;
  const baseline=pinnedReport, candidate=report, button=$('export-comparison');
  const request={case:candidate.case,baseline_plan:baseline.plan,candidate_plan:candidate.plan,
    baseline_plan_hash:baseline.plan_hash,candidate_plan_hash:candidate.plan_hash,
    contract_hash:candidate.contract_hash};
  if(candidate.case==='custom')request.contract=importedContract;
  comparisonBusy=true;button.disabled=true;button.textContent='Replaying both plans…';
  try {
    const body=JSON.stringify(request);
    if(new Blob([body]).size>131072)throw Error('The paired contract and plans exceed the 128 KiB hosted request limit. Use the local CLI.');
    const response=await fetch('/api/comparison-bundle',{method:'POST',headers:{'Content-Type':'application/json'},body});
    if(!response.ok){const data=await response.json();throw Error(data.error||'Comparison packet failed.');}
    if(response.headers.get('Content-Type')!=='application/zip'||
       response.headers.get('X-Cutover-Baseline-SHA256')!==baseline.plan_hash||
       response.headers.get('X-Cutover-Candidate-SHA256')!==candidate.plan_hash||
       response.headers.get('X-Cutover-Contract-SHA256')!==candidate.contract_hash||
       response.headers.get('X-Cutover-Engine-SHA256')!==candidate.engine_sha256||
       response.headers.get('X-Cutover-Suite-SHA256')!==candidate.suite_hash||
       response.headers.get('X-Cutover-Baseline-Status')!==baseline.status||
       response.headers.get('X-Cutover-Candidate-Status')!==candidate.status||
       response.headers.get('X-Cutover-Baseline-Coverage')!==`${baseline.passed}/${baseline.total}`||
       response.headers.get('X-Cutover-Candidate-Coverage')!==`${candidate.passed}/${candidate.total}`)
      throw Error('Fresh paired evidence differs from the displayed comparison. Rerun both plans.');
    const packet=await response.blob();
    if(report!==candidate||pinnedReport!==baseline)throw Error('The displayed comparison changed during export. Rerun both plans.');
    download(`cutover-${candidate.case}-${baseline.plan_hash.slice(0,8)}-to-${candidate.plan_hash.slice(0,8)}.zip`,packet,'application/zip');
    notify('Both review packets downloaded from fresh, independently auditable rehearsals.');
  }catch(error){notify(error.message);}
  finally{comparisonBusy=false;button.textContent='Download both review packets ↓';renderComparison();}
});
$('export').addEventListener('click',()=>{if(!report)return;const {review_markdown,reproduction_python,...evidence}=report;download(`cutover-${report.case}-${report.plan_hash.slice(0,10)}.json`,pretty(evidence));});
$('export-repro').addEventListener('click',()=>report?.reproduction_python&&download(`cutover-${report.case}-${report.plan_hash.slice(0,10)}-replay.py`,report.reproduction_python,'text/x-python'));
$('export-review').addEventListener('click',()=>report?.review_markdown&&download(`cutover-${report.case}-${report.plan_hash.slice(0,10)}.md`,report.review_markdown,'text/markdown'));
$('save-plan').addEventListener('click',()=>download(`cutover-${activeCase.id}-candidate.json`,pretty(currentPlan())));
$('save-contract').addEventListener('click',()=>importedContract&&download(`cutover-${fileSlug(importedContract.project)}-contract.json`,pretty(importedContract)));
$('download-brief').addEventListener('click',()=>download('CUTOVER-BOB-TASK.txt',briefText,'text/plain'));
$('import-plan').addEventListener('change',async event=>{
  if(busy)return;
  const file=event.target.files[0]; if(!file)return;
  invalidate();
  try {if(file.size>65536)throw Error('Plan is larger than 64 KiB.'); const plan=JSON.parse(await file.text()); if(!plan||typeof plan!=='object'||Array.isArray(plan)||Object.keys(plan).sort().join(',')!==Object.keys(fields).sort().join(',')||Object.values(plan).some(v=>typeof v!=='string'||!v.trim()||v.length>12000)||plan.name.length>100) throw Error('Expected a plan with name, migration, read, write and insert strings.');reference=null;setPlan(plan,'Imported candidate · not yet executed','imported candidate');updateModeControls();notify('Candidate imported. Run a rehearsal to verify it.');}
  catch(error){$('status-badge').textContent='IMPORT ERROR';$('verdict-title').textContent='Plan not imported.';$('verdict-description').textContent=error.message;notify(error.message);}finally{event.target.value='';}
});
async function activateContract(contract, source) {
  if(!contract||typeof contract!=='object'||Array.isArray(contract))throw Error('Contract must be a JSON object.');
  const body=JSON.stringify({contract});
  if(new Blob([body]).size>65536)throw Error('Contract exceeds the 64 KiB hosted request limit. Use the local CLI.');
  const response=await fetch('/api/contract/validate',{method:'POST',headers:{'Content-Type':'application/json'},body});
  const result=await response.json(); if(!response.ok)throw Error(result.error||'Contract validation failed.');
  importedContract=contract; importedMeta=result; customPlan=null; customPlanSource=null; customPlanProvenance=null;
  let option=$('case').querySelector('option[value="custom"]');
  if(!option){option=document.createElement('option');option.value='custom';$('case').append(option);}
  option.textContent=`${contract.project} · ${source==='example'?'example':'imported'}`;
  $('case').value='custom'; chooseCase();
  $('contract-status').textContent=`${source==='example'?'Prewritten example · ':''}Validated ${result.seed_count} seed records · ${result.payload_count} inputs · contract ${result.contract_hash.slice(0,12)}`;
}
$('import-contract').addEventListener('change',async event=>{
  if(busy)return;
  const file=event.target.files[0]; if(!file)return;
  setBusy(true,'Validating contract…'); invalidate(); $('status-badge').textContent='CHECKING CONTRACT';
  try {
    if(file.size>65536)throw Error('Contract is larger than 64 KiB. Use the local CLI.');
    const contract=JSON.parse(await file.text());
    await activateContract(contract,'imported');
    notify('Contract validated. Import a candidate plan or enter its SQL, then run the rehearsal.');
  } catch(error) {
    $('status-badge').textContent='IMPORT ERROR'; $('verdict-title').textContent='Contract not imported.';
    $('verdict-description').textContent=error.message;
    $('contract-status').textContent=`Import rejected: ${error.message} ${importedMeta?'Previously validated contract remains available.':''}`;
    notify(error.message);
  } finally {event.target.value='';setBusy(false);}
});
$('try-warehouse').addEventListener('click',async()=>{
  if(busy)return;
  setBusy(true,'Loading warehouse example…'); invalidate(); $('status-badge').textContent='LOADING EXAMPLE';
  try {
    const response=await fetch('/api/example/warehouse');
    const data=await response.json(); if(!response.ok)throw Error(data.error||'Warehouse example unavailable.');
    await activateContract(data.contract,'example');
    reference=null;
    setPlan(data.plan,'Prewritten warehouse example · not AI generated','prewritten warehouse example');
    notify('Warehouse example loaded. Run the SQL rehearsal to see the unsafe migration window.');
  } catch(error) {
    $('status-badge').textContent='EXAMPLE ERROR'; $('verdict-title').textContent='Example not loaded.';
    $('verdict-description').textContent=error.message; notify(error.message);
  } finally {setBusy(false);}
});
try {const response=await fetch('/api/catalog');if(!response.ok)throw Error('Could not load sample projects.');catalog=await response.json();$('case').innerHTML=catalog.cases.map(c=>`<option value="${c.id}">${escape(c.project)}</option>`).join('');chooseCase();}
catch(error){$('verdict-title').textContent='Workspace unavailable.';$('verdict-description').textContent=error.message;$('run').disabled=true;notify(error.message);}
