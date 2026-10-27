// Requires ACCEPTANCE_HOLD_RUNNER=1 on the isolated synthetic browser harness.
// Exercises real app persistence/cancellation, with no remote runner dispatch.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
 const context=await browser.newContext({viewport:{width:360,height:800}});
 const page=await context.newPage();
 const base=process.env.FIELDNOTE_TEST_ORIGIN||'http://127.0.0.1:8003';
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 let sid,headers;
 try{
  const auth=await context.request.post(base+'/api/auth',{data:{token:'synthetic-browser-acceptance-owner-key'}});
  headers={'X-CSRF-Token':(await auth.json()).csrf_token};
  let settings=await(await context.request.get(base+'/api/settings')).json();
  settings.providers.groq.paid_opt_in=true;settings.provider='groq';
  assert.equal((await context.request.patch(base+'/api/settings',{headers,data:settings})).status(),200);
  assert.equal((await context.request.post(base+'/api/providers/groq/test',{headers,data:settings.providers.groq})).status(),200);
  for(const old of (await(await context.request.get(base+'/api/sessions')).json()).sessions)
   await context.request.delete(base+'/api/sessions/'+old.id,{headers});
  let session=await(await context.request.post(base+'/api/sessions',{headers,data:{
   context:'Built a product API.',claims:[{source_bullet:'Built a product API.',contribution:'Implemented request validation.'}],
   role:'backend',experience:'junior',cloud_consent:true,idempotency_key:crypto.randomUUID()}})).json();
  sid=session.id;assert.ok(sid);
  for(const action of ['advance','skip']){
   session=await(await context.request.get(base+'/api/sessions/'+sid)).json();
   const response=await context.request.post(base+`/api/sessions/${sid}/actions`,{headers,data:{action,expected_revision:session.revision,idempotency_key:crypto.randomUUID()}});
   assert.equal(response.status(),200,await response.text());
  }
  await page.goto(base);await page.getByRole('button',{name:'My interviews',exact:true}).click();
  await page.getByRole('button',{name:'Resume interview',exact:true}).click();
  await page.getByRole('heading',{name:'Count normalized event names',exact:true}).waitFor();
  await page.locator('.monaco-editor').waitFor();
  await page.locator('.monaco-editor').scrollIntoViewIfNeeded();
  const bar=page.locator('.task-voice-bar');
  const bounds=await bar.boundingBox();
  assert.ok(bounds&&bounds.y>=0&&bounds.y+bounds.height<=800,'Exercise voice controls scrolled out of view: '+JSON.stringify(bounds));
  assert.equal(await bar.locator('p').textContent(),await page.locator('.current-question h1').textContent());
  const stopped=page.waitForResponse(response=>response.url().endsWith('/actions')&&response.request().postDataJSON()?.action==='stop');
  await bar.getByRole('button',{name:'Stop interviewer',exact:true}).click();
  assert.equal((await stopped).status(),200);
  await page.getByRole('button',{name:'Submit immutable attempt',exact:true}).click();
  await page.getByRole('button',{name:'Cancel execution',exact:true}).waitFor();
  const cancelResponse=page.waitForResponse(response=>response.url().endsWith('/cancel')&&response.request().method()==='POST');
  await page.getByRole('button',{name:'Cancel execution',exact:true}).click();
  const cancelled=await cancelResponse;assert.equal(cancelled.status(),200,await cancelled.text());
  const saved=await cancelled.json();assert.equal(saved.submission.status,'cancelled');
  assert.match(saved.submission.source,/def solve/);
  await page.getByText('Cancelled by the candidate. Remote cleanup may still be pending; this is not a candidate failure.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Cancel execution',exact:true}).count(),0);
  const job=await(await context.request.get(base+'/api/submissions/'+saved.submission.id)).json();
  assert.equal(job.status,'cancelled');assert.equal(job.source,saved.submission.source);
  const report=await(await context.request.get(base+`/api/sessions/${sid}/report`)).json();
  assert.equal(report.coding_outcomes[0].status,'cancelled');
  assert.equal(report.timeline.filter(event=>event.kind==='submission_cancelled').length,1);
  const width=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  assert.equal(width.viewport,width.document);assert.deepEqual(errors,[]);
  await page.screenshot({path:'docs/screenshots/cancel-execution-mobile.png',fullPage:true});
  await page.locator('.submission-result').scrollIntoViewIfNeeded();
  await page.screenshot({path:'docs/screenshots/coding-sticky-controls-mobile.png'});
  const result={synthetic_provider:true,held_app_task_only:true,remote_dispatch:false,candidate_execution:false,
   browser_cancel:true,immutable_source_preserved:true,cancelled_report:true,single_cancellation_event:true,sticky_question_status_stop:true,mobile:width,errors};
  await fs.writeFile('docs/browser-cancel-execution-results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{
  if(sid)await context.request.delete(base+'/api/sessions/'+sid,{headers});
  await browser.close();
 }
})().catch(error=>{console.error(error);process.exit(1)});
