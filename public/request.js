// Keep the deadline active while receiving the body, not just the headers.
// Each request is attempted once: retrying SQL or an export is a user action.
export async function request(url, init={}, {timeoutMs=120000, binary=false}={}) {
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try {
    const response=await fetch(url,{...init,signal:controller.signal});
    const json=response.headers.get('Content-Type')?.split(';')[0].trim()==='application/json';
    if(!response.ok) {
      let detail;
      if(json) {
        try {detail=(await response.json())?.error;}
        catch(error) {if(controller.signal.aborted)throw error;}
      }
      throw Error(typeof detail==='string'&&detail.trim()?detail:
        `The demo service returned HTTP ${response.status}. No new evidence was accepted. Try again shortly; your SQL is still in the editor.`);
    }
    if(!binary&&!json)throw Error('The demo returned an unexpected response. No new evidence was accepted. Try again shortly; your SQL is still in the editor.');
    const data=binary?await response.blob():await response.json();
    return {data,headers:response.headers};
  } catch(error) {
    if(controller.signal.aborted)throw Error('The request timed out. No new evidence was accepted. Your SQL is still in the editor; you can retry or export the plan for the local CLI.');
    if(error instanceof TypeError)throw Error('The demo could not be reached. Your SQL is still in the editor. Check your connection and try again.');
    if(error instanceof SyntaxError)throw Error('The demo returned incomplete evidence. No new result was accepted. Try again shortly.');
    throw error;
  } finally {clearTimeout(timer);}
}
