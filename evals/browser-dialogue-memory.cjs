// Synthetic provider and injected transcript mistakes. No microphone or runner.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
 const page=await browser.newPage({viewport:{width:360,height:800},reducedMotion:'reduce'});
 const base=process.env.FIELDNOTE_TEST_ORIGIN||'http://127.0.0.1:8005';
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const cases=[
  ['I invalidated the cash after the write.','I invalidated the cache after the write.'],
  ['I measured p50 latency.','I measured p95 latency.'],
  ['The expiry was sixty milliseconds.','The expiry was sixty seconds.'],
  ['I used key validation.','I used key invalidation.'],
  ['The read came from the primary.','The read came from the replica.'],
  ['I did retry failed invalidations.','I did not retry failed invalidations.'],
 ];
 try{
  await page.goto(base);
  const auth=await page.request.post(base+'/api/auth',{data:{token:'synthetic-browser-acceptance-owner-key'}});
  assert.ok(auth.ok());const headers={'X-CSRF-Token':(await auth.json()).csrf_token};
  async function request(method,path,data){
   const response=await page.request.fetch(base+path,{method,headers,data});
   assert.ok(response.ok(),path+': '+await response.text());return response.json();
  }
  for(const prior of (await request('GET','/api/sessions')).sessions){
   await request('DELETE','/api/sessions/'+prior.id);
  }
  const settings=await request('GET','/api/settings');
  settings.provider='groq';settings.providers.groq.paid_opt_in=true;
  await request('PATCH','/api/settings',settings);
  await request('POST','/api/providers/groq/test',settings.providers.groq);
  let session=await request('POST','/api/sessions',{
   context:'Synthetic product API and cache project.',claims:[{source_bullet:'Built a product API.',contribution:'Implemented cache policy.'}],
   role:'backend',experience:'junior',cloud_consent:true,idempotency_key:'memory-browser-'+Date.now()});
  async function settled(memory=false){
   for(let attempt=0;attempt<150;attempt++){
    session=await request('GET','/api/sessions/'+session.id);
    const last=session.turns.at(-1);
    if(last?.role==='assistant'&&last.delivery==='complete'&&session.turns.every(t=>t.delivery!=='generating')){
     if(!memory)return;
     const report=await request('GET','/api/sessions/'+session.id+'/report');
     if(report.conversation_memory.status==='provisional_conversational_coverage')return;
    }
    await new Promise(resolve=>setTimeout(resolve,200));
   }
   throw new Error('Timed out waiting for completed generation or memory');
  }
  await settled();
  for(const [original] of cases){
   session=await request('POST',`/api/sessions/${session.id}/answers`,{
    text:original,expected_revision:session.revision,idempotency_key:'answer-'+Date.now()});
   await settled();
  }
  await settled(true);
  const before=await request('GET',`/api/sessions/${session.id}/report`);
  assert.ok(before.conversation_memory.answered_points.length>0);
  assert.ok(before.conversation_memory.unresolved_details.length>0);
  session=await request('POST',`/api/sessions/${session.id}/actions`,{
   action:'end',expected_revision:session.revision,idempotency_key:'memory-end-'+Date.now()});
  await page.reload();
  await page.getByRole('button',{name:'My interviews',exact:true}).click();
  await page.getByRole('button',{name:'Open report',exact:true}).first().click();
  await page.getByRole('heading',{name:'Conversational coverage',exact:true}).waitFor();
  const coverage=page.locator('section').filter({has:page.getByRole('heading',{name:'Conversational coverage',exact:true})});
  await coverage.getByText('Addressed in conversation',{exact:true}).first().waitFor();
  await coverage.getByRole('heading',{name:'Conversational coverage',exact:true}).evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:'docs/screenshots/conversation-memory-mobile.png'});
  await page.setViewportSize({width:1440,height:1000});
  await coverage.getByRole('heading',{name:'Conversational coverage',exact:true}).evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:'docs/screenshots/conversation-memory-desktop.png'});
  await page.setViewportSize({width:360,height:800});
  const repairs=[];
  for(let index=0;index<cases.length;index++){
   const [original,corrected]=cases[index];
   page.once('dialog',dialog=>dialog.accept(corrected));
   await page.getByRole('button',{name:'Correct transcript',exact:true}).nth(index).click();
   await page.locator('#review-transcript article').nth(index).getByText(corrected,{exact:true}).first().waitFor();
   const report=await request('GET',`/api/sessions/${session.id}/report`);
   const turn=report.turns.filter(t=>t.role==='user')[index];
   assert.equal(turn.text,corrected);assert.equal(turn.version,2);
   assert.equal(turn.versions.find(v=>v.version===1).text,original);
   assert.equal(report.conversation_memory.status,'unavailable');
   assert.ok(report.findings.some(f=>f.utterance_id===turn.id&&f.source_version===1&&f.status==='stale'));
   assert.ok(report.findings.some(f=>f.utterance_id===turn.id&&f.source_version===2&&f.status==='reference_only'&&f.quote===corrected));
   assert.ok(report.criterion_coverage.every(c=>c.rating===null));
   repairs.push({original,corrected,version:turn.version,original_preserved:true,dependent_memory_invalidated:true});
  }
  await coverage.getByText('Conversational coverage is unavailable. Your full transcript and recorded open questions remain available.',{exact:true}).waitFor();
  const size=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  assert.equal(size.viewport,size.document);assert.deepEqual(errors,[]);
  const deletion=await request('DELETE','/api/sessions/'+session.id);assert.ok(deletion.deleted);
  const result={scope:'Synthetic provider, six injected recognition-like mistakes entered through the shared typed-answer path; no actual STT accuracy or human calibration claim.',
   memory_available_before_corrections:true,source_linked_grouping:true,repairs,all_ratings_null:true,deletion:true,mobile:size,errors};
  await fs.writeFile('docs/browser-dialogue-memory-results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
