const $ = id => document.getElementById(id);
let catalog, activeCase, reference = 'rename', report = null, selected = null, busy = false, briefText = '';
const fields = {name: 'plan-name', migration: 'migration', read: 'read', write: 'write', insert: 'insert'};
const labels = {compatibility: 'Old worker alive', mixed_versions: 'Mixed versions', rollback: 'Rollback reads', new_records: 'New records', interleaving: 'Write order', in_flight: 'Before migration', migration_window: 'Migration windows'};
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty = value => JSON.stringify(value, null, 2);
const currentPlan = () => Object.fromEntries(Object.entries(fields).map(([key, id]) => [key, $(id).value]));

function notify(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(notify.timer); notify.timer = setTimeout(() => $('toast').hidden = true, 5000); }
function download(name, content, type='application/json') { const url = URL.createObjectURL(new Blob([content], {type})); const a = document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); }
function setBusy(value) { busy=value; for (const node of document.querySelectorAll('.candidate-panel button,.candidate-panel textarea,.candidate-panel input,#case')) node.disabled=value; $('run').innerHTML=value?'<span>Executing SQL rehearsals…</span><span>◌</span>':'<span>Run release rehearsal</span><span>↗</span>'; }

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
  $('finding').innerHTML='<span class="finding-icon">↳</span><div><h3>Evidence, before assurance.</h3><p>Every result comes from executed SQL and an independent record of acknowledged writes.</p></div>';
  $('export').disabled=true; $('brief').disabled=true;
}
function setPlan(plan, source) {
  Object.entries(fields).forEach(([key,id])=>$(id).value=plan[key]);
  $('source-label').textContent=source;
  document.querySelectorAll('[data-plan]').forEach(button=>{ const chosen=button.dataset.plan===reference; button.classList.toggle('selected',chosen); button.setAttribute('aria-pressed',String(chosen)); });
  invalidate();
}
function chooseCase() {
  activeCase=catalog.cases.find(c=>c.id===$('case').value); reference='rename';
  $('case-description').textContent=activeCase.summary;
  $('old-contract').textContent=pretty(activeCase.old);
  setPlan(activeCase.plans.rename,'Editable reference');
}

async function run() {
  if(busy) return;
  const plan=currentPlan(), caseId=activeCase.id;
  setBusy(true); invalidate(); $('status-badge').textContent='RUNNING';
  try {
    const response=await fetch('/api/rehearse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case:caseId,plan})});
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
  $('source-label').textContent=`Executed · ${report.plan_hash.slice(0,10)}`;
  $('status-badge').textContent=passed?'SUITE PASSED':'BLOCKED'; $('status-badge').className=`status-badge ${report.status}`;
  $('verdict-title').textContent=passed?'The handover holds.':'The handover breaks.';
  $('verdict-description').textContent=passed?'Both versions observed the expected data in every tested schedule and migration window. Keep the bridge through the rollback window.':completePassed===completeTotal&&windows?.passed<windows?.total?`All ${completeTotal} completed-rollout probes passed. ${windows.total-windows.passed} migration-window probes failed: an old write can arrive before synchronization is in place.`:`${report.failed} probes failed. ${report.baseline.passed===report.baseline.total?'A green new-version baseline does not establish that old and new workers can safely share the data.':'The new-version baseline also fails; this candidate does not meet the required target-column contract.'}`;
  $('baseline-count').innerHTML=`${report.baseline.passed}<small> / ${report.baseline.total}</small>`;
  $('baseline-count').className=report.baseline.passed===report.baseline.total?'green':'red';
  $('baseline-note').textContent=report.baseline.passed===report.baseline.total?'✓ Same-version checks pass':'× Same-version failures';
  $('probe-count').innerHTML=`${report.passed}<small> / ${report.total}</small>`; $('probe-count').className=passed?'green':'red';
  $('probe-note').textContent=passed?'✓ All tested schedules pass':`× ${report.failed} failed probes`;
  $('runtime').textContent=`${report.duration_ms} ms engine time`;
  $('coverage').innerHTML=report.categories.map(c=>`<div class="coverage-row"><span>${escape(labels[c.id])}</span><div class="meter" aria-label="${c.passed} of ${c.total} passed">${Array.from({length:c.total},(_,i)=>`<i class="${i<c.passed?'good':'bad'}"></i>`).join('')}</div><span>${c.passed}/${c.total}</span></div>`).join('');
  const witness=report.witness;
  $('finding').innerHTML=`<span class="finding-icon">${passed?'✓':'↳'}</span><div><h3>${passed?'Passing evidence, with a boundary.':witness.failure.kind==='data_mismatch'?'The SQL worked. The data disagreed.':['adapter_contract','target_contract','target_mismatch'].includes(witness.failure.kind)?'The target contract is unmet.':'A real query fails during handover.'}</h3><p>${passed?`${report.total} probes passed on this sample contract. This does not certify untested workloads or another database engine.`:escape(witness.failure.message)}</p></div>`;
  $('export').disabled=false; $('brief').disabled=false;
  $('hashes').textContent=`Plan SHA-256: ${report.plan_hash} · Contract SHA-256: ${report.contract_hash} · Suite SHA-256: ${report.suite_hash}`;
  renderMatrix(); renderTrace(witness || report.results.find(r=>r.id==='new_to_old-0'));
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
  $('trace-payload').textContent=`Input: ${JSON.stringify(probe.payload)}`;
  $('trace').innerHTML=probe.trace.map(event=>`<div class="trace-step ${event.status}"><h4>${escape(event.action)}</h4><p>${escape(event.detail||'Executed.')}</p><details><summary>Executed SQL${event.params?' & inputs':''}</summary><pre>${escape(event.sql)}${event.params?'\n\n'+escape(pretty(event.params)):''}</pre></details>${event.status==='fail'&&event.actual?`<div class="comparison"><div class="expected">EXPECTED ${escape(pretty(event.expected))}</div><div class="actual">OBSERVED ${escape(pretty(event.actual))}</div></div>`:''}</div>`).join('');
  document.querySelectorAll('[data-probe]').forEach(b=>b.classList.toggle('chosen',b.dataset.probe===selected));
}
async function showBob() {
  const intro=`Inspect this Cutover project and repair the ${activeCase?.id||'parcel'} rollout. Use inspect_release and rehearse_candidate through the Cutover MCP server. Preserve the fixed old contract and the evaluator. Save your candidate to work/bob-candidate.json. Explain each change and retain your actual Bob task summary and screenshots. Do not claim that prewritten reference solutions are your work.\n\n`;
  if(report) {
    briefText=intro+pretty({case:report.case,plan_hash:report.plan_hash,candidate:report.plan,shortest_observed_witness:report.witness,constraints:['Preserve old/new updates and inserts.','Application rollback must preserve new-version writes.','Protect old writes at every migration statement boundary.','Do not change the old adapter, oracle, seeds or suite to make a plan pass.',`Rerun all ${report.total} probes, then report coverage limits.`]});
  } else briefText=intro+'Begin with the rename candidate. The task is to produce an evidence-backed repair, not to generate a risk score.';
  $('bob-task').value=briefText; $('bob-dialog').showModal();
}

$('run').addEventListener('click',run);
$('case').addEventListener('change',chooseCase);
document.querySelectorAll('[data-plan]').forEach(button=>button.addEventListener('click',()=>{if(busy)return;reference=button.dataset.plan;setPlan(activeCase.plans[reference],'Editable reference · not AI generated');}));
Object.values(fields).forEach(id=>$(id).addEventListener('input',()=>{reference=null;$('source-label').textContent='Custom candidate · not yet executed';document.querySelectorAll('[data-plan]').forEach(b=>{b.classList.remove('selected');b.setAttribute('aria-pressed','false');});invalidate();}));
$('failures-only').addEventListener('change',renderMatrix);
$('brief').addEventListener('click',showBob); $('bob-nav').addEventListener('click',showBob);
$('export').addEventListener('click',()=>report&&download(`cutover-${report.case}-${report.plan_hash.slice(0,10)}.json`,pretty(report)));
$('save-plan').addEventListener('click',()=>download(`cutover-${activeCase.id}-candidate.json`,pretty(currentPlan())));
$('download-brief').addEventListener('click',()=>download('CUTOVER-BOB-TASK.txt',briefText,'text/plain'));
$('import-plan').addEventListener('change',async event=>{
  if(busy)return;
  const file=event.target.files[0]; if(!file)return;
  try {if(file.size>65536)throw Error('Plan is larger than 64 KiB.'); const plan=JSON.parse(await file.text()); if(Object.keys(plan).sort().join(',')!==Object.keys(fields).sort().join(',')||Object.values(plan).some(v=>typeof v!=='string'||!v.trim()||v.length>12000)||plan.name.length>100) throw Error('Expected a plan with name, migration, read, write and insert strings.');reference=null;setPlan(plan,'Imported candidate · not yet executed');notify('Candidate imported. Run a rehearsal to verify it.');}
  catch(error){notify(error.message);}finally{event.target.value='';}
});
try {const response=await fetch('/api/catalog');if(!response.ok)throw Error('Could not load sample projects.');catalog=await response.json();$('case').innerHTML=catalog.cases.map(c=>`<option value="${c.id}">${escape(c.project)}</option>`).join('');chooseCase();document.querySelectorAll('[data-plan]').forEach(button=>button.disabled=false);$('run').disabled=false;}
catch(error){$('verdict-title').textContent='Workspace unavailable.';$('verdict-description').textContent=error.message;$('run').disabled=true;notify(error.message);}
