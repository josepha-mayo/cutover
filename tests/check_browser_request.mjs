import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {request} from '../public/request.js';

const calls=new Map();
const server=createServer((req,res)=>{
  calls.set(req.url,(calls.get(req.url)||0)+1);
  if(req.url==='/headers-stall')return;
  if(req.url==='/body-stall'){
    res.writeHead(200,{'Content-Type':'application/json'});
    res.write('{"partial":');return;
  }
  if(req.url==='/binary-stall'){
    res.writeHead(200,{'Content-Type':'application/zip'});
    res.write('PK');return;
  }
  if(req.url==='/unavailable'){
    res.writeHead(503,{'Content-Type':'text/html'});
    res.end('<h1>Wake up</h1>');return;
  }
  if(req.url==='/unexpected'){
    res.writeHead(200,{'Content-Type':'text/html'});
    res.end('<h1>Proxy page</h1>');return;
  }
  if(req.url==='/busy'){
    res.writeHead(503,{'Content-Type':'application/json'});
    res.end(JSON.stringify({error:'Both rehearsal slots are occupied. Retry shortly.'}));return;
  }
  if(req.url==='/broken-json'){
    res.writeHead(200,{'Content-Type':'application/json'});
    res.end('{"status":');return;
  }
  if(req.url==='/packet'){
    res.writeHead(200,{'Content-Type':'application/zip','X-Review':'measured'});
    res.end(Buffer.from([80,75,0,255]));return;
  }
  res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','X-Review':'measured'});
  res.end(JSON.stringify({status:'blocked',passed:80,total:116}));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const mode=process.argv[2];
try {
  if(mode==='success'){
    const result=await request(base+'/result');
    assert.deepEqual(result.data,{status:'blocked',passed:80,total:116});
    assert.equal(result.headers.get('X-Review'),'measured');
    const packet=await request(base+'/packet',{}, {binary:true});
    assert.deepEqual([...new Uint8Array(await packet.data.arrayBuffer())],[80,75,0,255]);
    assert.equal(packet.headers.get('Content-Type'),'application/zip');
  }else if(mode==='errors'){
    await assert.rejects(request(base+'/unavailable'),/HTTP 503.*No new evidence/);
    await assert.rejects(request(base+'/unexpected'),/unexpected response.*No new evidence/);
    await assert.rejects(request(base+'/busy'),/Both rehearsal slots are occupied/);
    await assert.rejects(request(base+'/broken-json'),/incomplete evidence.*No new result/);
    // A later explicit request works; the helper never retries on its own.
    assert.equal((await request(base+'/result')).data.status,'blocked');
  }else if(mode==='deadlines'){
    for(const path of ['/headers-stall','/body-stall','/binary-stall']){
      await assert.rejects(request(base+path,{}, {timeoutMs:250,binary:path==='/binary-stall'}),/timed out.*No new evidence/);
    }
    assert.equal((await request(base+'/result')).data.total,116);
  }else throw Error('Unknown test mode');
  for(const count of calls.values())assert.equal(count,1,'Request was silently retried');
  console.log(JSON.stringify({ok:true,mode,calls:Object.fromEntries(calls)}));
}finally{
  server.closeAllConnections();
  await new Promise(resolve=>server.close(resolve));
}
