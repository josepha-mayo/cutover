"""Render audited reports as a self-contained, non-executing offline review."""
import base64
import difflib
import hashlib
import html
import json


STYLE = '''
*{box-sizing:border-box}body{margin:0;background:#f4f5ef;color:#17211f;font:15px/1.6 system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:28px}h1{font-size:34px;line-height:1.2}h2{font-size:20px}
.scope{color:#58665b;font-size:13px}.cards,.columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
article,section{padding:20px;background:#fffefa;border:1px solid #dfe3d8;border-radius:7px;margin:16px 0}
.blocked{border-left:4px solid #ad403a}.pass{border-left:4px solid #427d5e}label{display:block;margin:10px 0;font-weight:600}
select,input,button{font:inherit;max-width:100%;min-height:44px}select{width:100%;padding:8px}input[type=range]{width:100%;accent-color:#ea653a}
button{padding:8px 15px;margin-right:8px;background:#f4f5ef;border:1px solid #bac7b8;border-radius:4px;cursor:pointer}
button:disabled{opacity:.45;cursor:default}:focus-visible{outline:3px solid #ea653a;outline-offset:3px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f5ef;padding:14px;font:12px/1.6 monospace;max-height:360px;overflow:auto}
code,.identity{overflow-wrap:anywhere}.identity{font:11px/1.6 monospace;color:#58665b}summary{cursor:pointer;min-height:44px}
.observations{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.observations>div{min-width:0}
@media(max-width:650px){main{padding:16px}.cards,.columns,.observations{grid-template-columns:minmax(0,1fr)}h1{font-size:28px}}
'''

SCRIPT = '''
const reports=JSON.parse(document.getElementById('recorded-data').textContent);
const $=id=>document.getElementById(id);
const text=(tag,value,parent)=>{const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;};
let current=0, selected=null, step=0;
reports.forEach((r,i)=>{
  const label=reports.length===1?'Executed plan':i===0?'Baseline':'Candidate';
  const card=document.createElement('article');card.className=r.status;
  text('h2',`${label}: ${r.status.toUpperCase()} ${r.passed}/${r.total}`,card);
  const window=r.categories.find(c=>c.id==='migration_window');
  text('p',`New-version checks: ${r.baseline.passed}/${r.baseline.total}. Completed-rollout checks: ${r.passed-window.passed}/${r.total-window.total}. Migration-window checks: ${window.passed}/${window.total}.`,card);
  text('p','Plan SHA-256: '+r.plan_hash,card).className='identity';
  $('summary').append(card);
  const option=document.createElement('option');option.value=i;option.textContent=label+' · '+r.plan.name+' · '+r.status;$('plan').append(option);
});
function chooseProbe(){
  const r=reports[current];selected=r.results.find(p=>p.id===$('probe').value);
  step=Math.max(0,selected.trace.findIndex(e=>e.status==='fail'));renderStep();
}
function choosePlan(){
  const r=reports[current];$('probe').replaceChildren();
  const probes=r.results.filter(p=>!$('failures').checked||!p.passed);
  probes.forEach(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=`${p.passed?'PASS':'FAIL'} · ${p.title} · input ${JSON.stringify(p.payload)}`;$('probe').append(o);});
  $('probe').disabled=!probes.length;$('empty').hidden=!!probes.length;$('walk').hidden=!probes.length;
  $('identity').textContent=`Contract SHA-256: ${r.contract_hash} · Suite SHA-256: ${r.suite_hash} · Engine SHA-256: ${r.engine_sha256}`;
  $('sql').replaceChildren();['migration','read','write','insert'].forEach(key=>{text('h3',key,$('sql'));text('pre',r.plan[key],$('sql'));});
  if(probes.length){$('probe').value=probes.some(p=>p.id===r.witness?.id)?r.witness.id:probes[0].id;chooseProbe();}
}
function renderStep(){
  if(!selected.trace.length){$('position').disabled=true;$('previous').disabled=true;$('next').disabled=true;$('event').replaceChildren();text('p','No executed steps were retained for this probe.',$('event'));return;}
  $('position').disabled=false;
  step=Math.max(0,Math.min(selected.trace.length-1,step));const e=selected.trace[step];
  $('position').max=Math.max(0,selected.trace.length-1);$('position').value=step;
  $('position').setAttribute('aria-valuetext',`Step ${step+1} of ${selected.trace.length}: ${e.action}`);
  $('previous').disabled=step===0;$('next').disabled=step===selected.trace.length-1;
  $('event').replaceChildren();
  text('h2',`Step ${step+1}/${selected.trace.length}: ${e.action} · ${e.status}`,$('event'));
  text('p',(e.detail||'Executed.')+(e.connection?' · '+e.connection+' connection':''),$('event'));
  text('pre',e.sql||'No SQL recorded for this event.',$('event'));
  if(e.params){text('h3','Executed inputs',$('event'));text('pre',JSON.stringify(e.params,null,2),$('event'));}
  if(Object.hasOwn(e,'expected')&&Object.hasOwn(e,'actual')){
    const pair=document.createElement('div');pair.className='observations';$('event').append(pair);
    [['Expected by contract',e.expected],['Reader observed',e.actual]].forEach(([label,values])=>{const col=document.createElement('div');pair.append(col);text('h3',label,col);text('pre',JSON.stringify(values,null,2),col);});
  }else text('p','No row values recorded at this step. Inputs are not a database snapshot.',$('event'));
}
$('plan').onchange=()=>{current=Number($('plan').value);choosePlan();};
$('failures').onchange=choosePlan;$('probe').onchange=chooseProbe;
$('position').oninput=()=>{step=Number($('position').value);renderStep();};
$('previous').onclick=()=>{step--;renderStep();};$('next').onclick=()=>{step++;renderStep();};
choosePlan();
'''


def content_security_policy():
    def digest(source):
        return base64.b64encode(hashlib.sha256(source.encode('utf-8')).digest()).decode('ascii')
    return (f"default-src 'none'; script-src 'sha256-{digest(SCRIPT)}'; "
              f"style-src 'sha256-{digest(STYLE)}'; base-uri 'none'; form-action 'none'")


def render_review(reports, baseline_git=None, candidate_sql_source=None):
    """Caller must independently audit reports before presenting this export."""
    reports = list(reports)
    payload = json.dumps(reports, ensure_ascii=True, separators=(',', ':'))
    payload = payload.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    policy = content_security_policy()
    provenance = ''
    changes = ''
    if len(reports) == 2:
        changed_fields = []
        for key in ('migration', 'read', 'write', 'insert'):
            before, after = (report['plan'][key] for report in reports)
            if before == after:
                continue
            delta = '\n'.join(difflib.unified_diff(before.splitlines(), after.splitlines(),
                              fromfile='baseline/'+key, tofile='candidate/'+key, lineterm=''))
            changed_fields.append('<h3>'+key+'</h3><pre>'+html.escape(delta or
                                  'Only line endings or final newline differ; no SQL line text changed.')+'</pre>')
        changes = ('<section><details><summary>Changed SQL: baseline → candidate</summary>'
                   '<p class="scope">Textual differences in the executed plans. These lines do not establish causality. '
                   'Only this display normalizes line endings; complete original SQL remains below and in the packet.</p>'+
                   (''.join(changed_fields) or '<p>No SQL fields changed between these executed plans.</p>')+
                   '</details></section>')
    if baseline_git is not None:
        fields = ''.join('<dt>'+label+'</dt><dd class="identity">'+html.escape(str(baseline_git[key]))+'</dd>'
                         for label, key in [('Commit', 'commit'), ('Repository SQL path', 'path'), ('Git blob', 'blob')])
        provenance = ('<section><h2>Original SQL reviewed</h2><dl>'+fields+'</dl>'
                      '<p class="scope">Local Git snapshot, not a signature. Only baseline migration SQL comes from this commit; '
                      'adapters and contract are supplied project inputs. Exact SQL bytes are retained in '
                      '<code>inputs/supplied-baseline.sql</code>. This does not verify the whole application at that commit.</p></section>')
    if candidate_sql_source is not None:
        fields = ''.join('<dt>'+label+'</dt><dd class="identity">'+html.escape(str(candidate_sql_source[key]))+'</dd>'
                         for label, key in [('Source file', 'path'), ('Path scope', 'path_scope'),
                                            ('Retained snapshot', 'snapshot'), ('SQL byte SHA-256', 'sha256')])
        provenance += ('<section><h2>Candidate SQL reviewed</h2><dl>'+fields+'</dl>'
                       '<p class="scope">Byte hash includes any BOM and line endings. The candidate executes this retained snapshot; '
                       'adapters still come from candidate.json. This does not verify the whole PR and is not a signature.</p></section>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{policy}"><title>Cutover recorded review</title><style>{STYLE}</style></head>
<body><main><h1>Follow the write. Review the migration.</h1>
<p class="scope">Offline review generated after independent replay. This page displays recorded evidence; it does not execute SQL or reverify itself. No network access is required. The HTML is not signed.</p>
<p class="scope">Sequential SQLite schedules only. Passing does not establish production safety, simultaneous transaction behavior or another database engine. Different migration sequences have their own statement boundaries; window probes are not paired by step number.</p>
{provenance}<div id="summary" class="cards"></div>{changes}<section><label for="plan">Executed plan</label><select id="plan"></select>
<p id="identity" class="identity"></p><label><input id="failures" type="checkbox"> Show failed probes only</label>
<label for="probe">Recorded probe</label><select id="probe"></select><p id="empty" hidden>No failed probes in this report. Clear the filter to inspect passing executions.</p>
<div id="walk"><label for="position">Replay step</label><input id="position" type="range" min="0" value="0">
<button id="previous" type="button">Previous step</button><button id="next" type="button">Next step</button><div id="event" aria-live="polite"></div></div>
<details><summary>Full executed SQL for selected plan</summary><div id="sql"></div></details></section>
<noscript><p>JavaScript is disabled. Read the companion Markdown and JSON for the complete evidence.</p></noscript></main>
<script id="recorded-data" type="application/json">{payload}</script><script>{SCRIPT}</script></body></html>
'''
