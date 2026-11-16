import fs from 'node:fs';
import http from 'node:http';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const ts = require('/Applications/Cursor.app/Contents/Resources/app/extensions/node_modules/typescript/lib/typescript.js');
const {chromium} = require('/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const canvas = '/Users/joshua/.cursor/projects/Users-joshua-Documents-ChatGPT-synthetic-society-lab/canvases/research-status-latest-20261116.canvas.tsx';
const root = '/Users/joshua/Documents/ChatGPT/synthetic-society-lab/';
const out = root + 'data/processed/status_canvas_qa_latest_20261116/';
fs.mkdirSync(out, {recursive:false});
const input = fs.readFileSync(canvas, 'utf8');
const options = {
  noEmit:true, strict:true, skipLibCheck:true, target:ts.ScriptTarget.ES2022,
  module:ts.ModuleKind.ESNext, moduleResolution:ts.ModuleResolutionKind.Bundler,
  jsx:ts.JsxEmit.ReactJSX, types:[], paths:{
    'cursor/canvas':['/Users/joshua/.cursor/skills-cursor/canvas/sdk/index.d.ts'],
    'react':['/Applications/Cursor.app/Contents/Resources/app/extensions/cursor-agent-exec/dist/agent-sdk/@types/react/index.d.ts'],
    'react/*':['/Applications/Cursor.app/Contents/Resources/app/extensions/cursor-agent-exec/dist/agent-sdk/@types/react/*']
  }
};
const program = ts.createProgram([canvas], options);
const diagnostics = ts.getPreEmitDiagnostics(program).map(d=>ts.flattenDiagnosticMessageText(d.messageText,'\n'));
fs.writeFileSync(out+'typecheck.json',JSON.stringify({diagnostics},null,2),{flag:'wx'});
if(diagnostics.length) throw new Error('TYPECHECK_FAILED');
const adapted = input.replace(/import\s*\{([^}]+)\}\s*from\s*"cursor\/canvas";/, 'const {$1} = globalThis;');
const compiled = ts.transpileModule(adapted,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.React}}).outputText;
const runtime = fs.readFileSync('/Applications/Cursor.app/Contents/Resources/app/extensions/cursor-agent-exec/dist/canvas-runtime/canvas-runtime.esm.js');
const requests=[]; const actions=[];
const html='<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0"><div id="root"></div><script>window.__cursorCanvas={canvasId:"status-qa",state:new Map(),data:new Map()};</script><script type="module">import{mountCanvas}from"/runtime.js";mountCanvas("/canvas.js");</script></body></html>';
const server=http.createServer((req,res)=>{
  requests.push({method:req.method,url:req.url});
  if(req.method==='POST'&&req.url==='/canvas/status-qa/action'){
    let b='';req.on('data',x=>{b+=x;if(b.length>8192)req.destroy();});req.on('end',()=>{actions.push(JSON.parse(b));res.writeHead(200,{'content-type':'application/json'});res.end('{}');});return;
  }
  const routes={'/':['text/html',html],'/runtime.js':['text/javascript',runtime],'/canvas.js':['text/javascript',compiled]};
  if(req.method!=='GET'||!routes[req.url]){res.writeHead(404);res.end();return;}
  const [type,body]=routes[req.url];res.writeHead(200,{'content-type':type});res.end(body);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
let browser;
const errors=[]; const checks=[];
try{
  browser=await chromium.launch({headless:true,channel:"chrome"});
  const page=await browser.newPage({viewport:{width:1100,height:1000}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>route.request().url().startsWith(origin+'/')?route.continue():route.abort());
  await page.goto(origin,{waitUntil:'networkidle',timeout:20000});
  await page.getByRole('heading',{name:'Synthetic Society Lab — status'}).waitFor({timeout:10000});
  for(const value of ['191','$0.0129589','$0.016149','14 BLOCKED','44 of at most 80 responses','2,771 unique ordinary tests']){
    if(!(await page.locator('body').innerText()).includes(value))throw new Error('MISSING_DISPLAY_VALUE');
  }
  checks.push('Headline and six key status/denominator values visible');
  await page.getByText('Verification, delivery and snapshot provenance',{exact:true}).click();
  await page.getByRole('button',{name:'Machine-readable checkpoint',exact:true}).waitFor();
  checks.push('Evidence disclosure opens');
  await page.getByRole('button',{name:'Billing diagnosis',exact:true}).click();
  await page.waitForTimeout(100);
  if(actions.length!==1||actions[0].type!=='openFile'||actions[0].path!==root+'reports/OPENROUTER_KEY_AND_ACCOUNT_DIAGNOSIS_20261116.json')throw new Error('SOURCE_ACTION_MISMATCH');
  checks.push('Source button dispatches correct openFile action to local stub; host opening not asserted');
  await page.screenshot({path:out+'desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(100);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
  await page.screenshot({path:out+'mobile-before-assert.png',fullPage:true});
  fs.writeFileSync(out+'width.json',JSON.stringify({overflow, elements:await page.locator('body *').evaluateAll(es=>es.filter(e=>e.getBoundingClientRect().right>390).slice(0,20).map(e=>({tag:e.tagName,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width,text:e.textContent.slice(0,80)})))}));
  if(overflow>2)throw new Error('BODY_HORIZONTAL_OVERFLOW');
  checks.push('390px layout has no document horizontal overflow');
  await page.screenshot({path:out+'mobile.png',fullPage:true});
  if(errors.length)throw new Error('BROWSER_ERRORS');
  fs.writeFileSync(out+'receipt.json',JSON.stringify({status:'PASS_LOCAL_TYPECHECK_AND_BUNDLED_RUNTIME_QA',canvas,canvas_bytes:Buffer.byteLength(input),canvas_sha256:crypto.createHash('sha256').update(input).digest('hex'),typescript_diagnostics:diagnostics,browser_errors:errors,checks,requests,actions,scope:'Static snapshot. Local bundled runtime; SDK import resolved through its documented globals. No model call, private data, live owner state or external service. Native host openFile behavior not independently verified.'},null,2),{flag:'wx'});
  console.log(JSON.stringify({status:'PASS',type_errors:0,browser_errors:0,checks:checks.length,output:out}));
}finally{
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
