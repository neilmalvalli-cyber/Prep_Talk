// Real configured provider, synthetic candidate data only. Never deletes other sessions.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const fullJourney=process.argv.includes('--full-journey');
const provider=process.env.FIELDNOTE_REAL_PROVIDER||'groq';
assert.ok(['groq','openrouter'].includes(provider));
const resultPath=provider==='groq'?(fullJourney?'docs/browser-real-provider-journey-results.json':'docs/browser-real-provider-dialogue-results.json'):
 `docs/browser-real-openrouter-${fullJourney?'journey':'dialogue'}-results.json`;

(async()=>{
 const base='http://localhost:8000';
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage(),errors=[],microphone=[],owned=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('dialog',dialog=>dialog.accept(dialog.type()==='prompt'?
  (dialog.message().startsWith('Correct')?'I used a TTL only; corrected synthetic transcript.':'Synthetic challenge: preserve the corrected context.'):
  undefined));
 page.on('request',request=>{if(/\/api\/(offer|voice\/warmup)/.test(request.url()))microphone.push(request.url())});
 let headers;
 const result={real_provider:true,synthetic_resume_and_answers:true,physical_microphone:false,
  runner_execution:false,cases:[],explicit_rate_limit_recoveries:[],errors};
 async function state(sid){const response=await context.request.get(`${base}/api/sessions/${sid}`);assert.ok(response.ok());return response.json()}
 async function completed(sid,count){
  const deadline=Date.now()+60000;
  while(Date.now()<deadline){
   const value=await state(sid);
   if(value.last_error&&value.paused){
    const seconds=Number(value.last_error.retry_after);
    if(value.last_error.code==='rate_limit'&&seconds>0&&seconds<=60&&result.explicit_rate_limit_recoveries.length<2){
     result.explicit_rate_limit_recoveries.push({retry_after_seconds:seconds,stage:value.stage});
     await page.waitForTimeout(seconds*1000+250);
     await page.getByRole('button',{name:'Resume interview',exact:true}).click();
     await page.getByRole('button',{name:'Retry explicitly',exact:true}).click();
     continue;
    }
    assert.equal(value.last_error,null,JSON.stringify(value.last_error));
   }
   if(value.turns.filter(turn=>turn.role==='assistant'&&turn.delivery==='complete').length>=count)return value;
   await page.waitForTimeout(250);
  }
  throw new Error('Real provider did not complete the expected question');
 }
 try{
  const login=await context.request.post(base+'/api/auth',{data:{token:(await fs.readFile('data/owner.key','utf8')).trim()}});
  assert.ok(login.ok());headers={'X-CSRF-Token':(await login.json()).csrf_token};
  const settings=await(await context.request.get(base+'/api/settings')).json();
  assert.equal(settings.provider,provider,'Run against the explicitly approved selected configuration');
  result.provider=settings.provider;result.configuration=settings.providers[provider];
  const resume='Built a search product with an API and browser interface. I implemented result caching and client-side state updates.';
  for(const role of ['backend','frontend'])for(const variant of ['ttl','invalidation']){
   if(fullJourney&&(role!=='backend'||variant!=='ttl'))continue;
   const answer=variant==='ttl'?'I used a TTL only. Cached results could remain stale until expiry.':
    'I explicitly invalidated the cached results after a successful write.';
   const created=await context.request.post(base+'/api/sessions',{headers,data:{
    context:resume,claims:[{source_bullet:resume,contribution:resume,offset:0}],role,experience:'junior',
    cloud_consent:true,record_audio:false,idempotency_key:crypto.randomUUID(),retention:'30_days'}});
   assert.ok(created.ok(),await created.text());
   const session=await created.json();owned.push(session.id);
   await page.goto(base);
   await page.getByRole('button',{name:'My interviews',exact:true}).click();
   const row=page.locator('.history-row').first();
   await row.getByRole('button',{name:'Resume interview',exact:true}).click();
   await page.getByLabel('Type your answer').waitFor();
   const initial=await completed(session.id,1);
   const first=initial.turns.filter(turn=>turn.role==='assistant'&&turn.delivery==='complete').at(-1).text;
   await page.evaluate(()=>{
    window.realProviderObserved=[];
    const heading=document.querySelector('.current-question h1');
    window.realProviderObserver=new MutationObserver(()=>window.realProviderObserved.push(heading.textContent));
    window.realProviderObserver.observe(heading,{childList:true,subtree:true,characterData:true});
   });
   await page.getByLabel('Type your answer').fill(answer);
   await page.getByRole('button',{name:'Send answer',exact:true}).click();
   const after=await completed(session.id,2);
   const followup=after.turns.filter(turn=>turn.role==='assistant').at(-1);
   await page.getByRole('heading',{name:followup.text.trim(),exact:true}).waitFor();
   assert.notEqual(first.trim(),followup.text.trim());
   assert.equal(after.snapshot.provider,provider);
   const observed=await page.evaluate(()=>{window.realProviderObserver.disconnect();return window.realProviderObserved});
   result.cases.push({role,answer_variant:variant,confirmed_resume:resume,answer,
    opening_question:first,followup:followup.text,followup_timing:followup.timing,
    distinct_browser_text_updates:new Set(observed).size,
    incremental_text_observed:observed.some(text=>text.trim()&&text.trim()!==first.trim()&&text.trim()!==followup.text.trim())});
   await page.screenshot({path:`docs/screenshots/real-${provider}-${role}-${variant}.png`,fullPage:true});
   if(fullJourney){
    const click=name=>page.getByRole('button',{name,exact:true}).first().click();
    const stage=name=>page.getByRole('heading',{name,exact:true}).waitFor();
    await click('Pause interview');await page.getByRole('button',{name:'Resume interview',exact:true}).waitFor();
    await click('Resume interview');
    await click('Confirm and continue to next stage');await stage('Synthetic exercise: a stale price response');
    await page.getByRole('button',{name:/Request .*key trace/}).click();
    await page.getByText('The reader looks up product:42:v7. The write invalidation deletes product:42.',{exact:true}).waitFor();
    await page.getByLabel('Provisional explanation or justified revision').fill('The reader and invalidator use different keys.');
    await click('Confirm hypothesis');
    await page.getByLabel('Conclusion and verification plan').fill('Compare the exact keys, align their construction, and test the request after a write.');
    await click('Confirm conclusion');await click('Confirm and continue to next stage');await stage('Count normalized event names');
    await page.getByLabel('Language',{exact:true}).selectOption('cpp');
    await page.locator('.view-lines').filter({hasText:'return 0;'}).waitFor();
    await page.getByLabel('Language',{exact:true}).selectOption('python');
    await page.locator('.view-lines').filter({hasText:'def solve():'}).waitFor();
    await click('Explicitly skip this stage');await stage('Authored reference review');
    await page.getByLabel('Next practice objective').fill('Compare request-level evidence with aggregate dashboards.');
    await click('Set practice objective');await click('Confirm and continue to next stage');await stage('Coached practice: compare evidence scopes');
    await click('Request authored hint');await click('Confirm and continue to next stage');
    await stage('Fresh transfer exercise: a stale price response');
    await page.getByLabel('Conclusion and verification plan').fill('Trace the request and replica version before changing cache policy.');
    await click('Confirm conclusion');await click('Confirm and continue to next stage');
    await click('Complete interview');await stage('Your practice, with the evidence attached.');
    await click('Correct transcript');
    await page.getByText('I used a TTL only; corrected synthetic transcript.',{exact:true}).first().waitFor();
    await page.locator('.finding').filter({hasText:'I used a TTL only; corrected synthetic transcript.'})
     .getByRole('button',{name:'Challenge observation',exact:true}).click();
    await page.getByText('disputed',{exact:true}).first().waitFor();
    const response=await context.request.get(`${base}/api/sessions/${session.id}/report`);assert.ok(response.ok());
    const report=await response.json();
    assert.equal(report.criterion_coverage.length,10);
    assert.ok(report.criterion_coverage.every(item=>item.rating===null));
    await page.screenshot({path:`docs/screenshots/real-${provider}-report-desktop.png`,fullPage:true});
    await page.setViewportSize({width:360,height:800});
    await page.screenshot({path:`docs/screenshots/real-${provider}-report-mobile.png`,fullPage:true});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),360);
    result.full_journey={pause_resume:true,baseline_evidence_and_conclusion:true,python_cpp_editor:true,
     coding_explicitly_skipped:true,authored_review:true,candidate_selected_objective:true,coached_hint:true,
     fresh_conclusion:true,completed_report:true,criterion_count:10,numeric_ratings_disabled:true,
     versioned_correction_and_dispute:true,mobile_width:360};
   }
   const deleted=await context.request.delete(`${base}/api/sessions/${session.id}`,{headers});assert.ok(deleted.ok());
   owned.splice(owned.indexOf(session.id),1);
   await fs.writeFile(resultPath,JSON.stringify(result,null,2));
   console.log(JSON.stringify({role,variant,opening_question:first,followup:followup.text}));
  }
  assert.deepEqual(errors,[]);assert.deepEqual(microphone,[]);
  result.microphone_calls=microphone;
  result.scope=`Actual ${provider} browser dialogue using synthetic context. Outputs require qualitative review; no assessment calibration or dedicated-runner claim.`;
  await fs.writeFile(resultPath,JSON.stringify(result,null,2));
 }catch(error){
  result.failure=error.message;
  if(owned.length){
   const current=await state(owned.at(-1));
   result.failure_state={stage:current.stage,paused:current.paused,last_error:current.last_error,
    turns:current.turns};
  }
  await page.screenshot({path:'docs/screenshots/real-provider-journey-failure.png',fullPage:true});
  await fs.writeFile(resultPath,JSON.stringify(result,null,2));
  throw error;
 }finally{
  for(const sid of owned)if(headers)await context.request.delete(`${base}/api/sessions/${sid}`,{headers});
  await browser.close();
 }
})().catch(error=>{console.error(error);process.exit(1)});
