// Chrome keyboard navigation acceptance with a synthetic provider and no runner.
// Native prompt/confirm dialogs use Playwright's dialog API; no screen-reader claim.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
 const page=await browser.newPage({viewport:{width:360,height:800},reducedMotion:'reduce'});
 const base=process.env.FIELDNOTE_TEST_ORIGIN||'http://127.0.0.1:8002';
 const errors=[],microphone=[],dialogs=[],checks=[];
 const contrast=[];
 async function auditContrast(screen){
  if(!process.env.AXE_CORE_SCRIPT)return;
  await page.waitForFunction(()=>{
   const control=document.querySelector('.interview-top .back-link');
   return !control||(!control.disabled&&getComputedStyle(control).opacity==='1');
  });
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  if(!await page.evaluate(()=>!!window.axe))await page.addScriptTag({path:process.env.AXE_CORE_SCRIPT});
  await page.evaluate(()=>document.fonts.ready);
  const scan=await page.evaluate(async()=>{
   const nodes=rules=>rules.flatMap(rule=>rule.nodes.map(node=>({target:node.target,html:node.html,
    summary:node.failureSummary,checks:[...node.any,...node.all,...node.none].map(check=>({id:check.id,data:check.data,message:check.message}))})));
   const run=async()=>{
    const result=await axe.run(document,{runOnly:{type:'rule',values:['color-contrast']}});
    return {axe_version:result.testEngine.version,violations:nodes(result.violations),incomplete:nodes(result.incomplete),
     passed_nodes:result.passes.reduce((count,rule)=>count+rule.nodes.length,0)};
   };
   const actual=await run(),body=getComputedStyle(document.body);
   const original={background_color:body.backgroundColor,background_image:body.backgroundImage};
   // Axe cannot resolve this radial gradient. Bound its entire color range:
   // transparent through rgba(47,83,122,.22), composited on rgb(16,29,53).
   // Only decorative background images are replaced for additional probes.
   // Keep actual-render results and any other indeterminate surfaces separate.
   if(body.backgroundColor!=='rgb(16, 29, 53)'||body.backgroundImage.split('gradient(').length!==2||
     !body.backgroundImage.includes('rgba(47, 83, 122, 0.22)')||!body.backgroundImage.includes('rgba(0, 0, 0, 0) 37%'))
    throw new Error('Body gradient changed; rederive contrast boundary colors before testing');
   const surfaces=[
    {selector:'.panel',colors:['rgba(23,40,65,.88)','rgba(28,47,75,.93)'],stops:['rgba(23,40,65,0.88)','rgba(28,47,75,0.93)']},
    {selector:'.aside-card',colors:['rgb(24,42,69)','rgb(29,52,84)']},
    {selector:'.sample-modal',colors:['rgb(23,41,65)','rgb(32,55,85)']},
    {selector:'.sample-question',colors:['rgba(24,43,70,.95)','rgba(33,57,88,.94)'],stops:['rgba(24,43,70,0.95)','rgba(33,57,88,0.94)']},
   ];
   for(const surface of surfaces){
    for(const element of document.querySelectorAll(surface.selector)){
     const image=getComputedStyle(element).backgroundImage.replaceAll(' ','');
     if(image.split('gradient(').length!==2||!(surface.stops||surface.colors).every(color=>image.includes(color)))
      throw new Error(`${surface.selector} gradient changed; rederive contrast boundary colors before testing`);
    }
   }
   const style=document.createElement('style');document.head.append(style);
   const boundaries=[];
   try{
    for(const [index,color] of ['rgb(16,29,53)','rgb(22.82,40.88,68.18)'].entries()){
     style.textContent=`body{background-image:none!important;background-color:${color}!important}`+
      surfaces.map(surface=>`${surface.selector}{background-image:none!important;background-color:${surface.colors[index]}!important}`).join('');
     boundaries.push({endpoint:index===0?'dark':'light',body_background_color:color,...await run()});
    }
   }finally{style.remove()}
   return {...actual,original_body_background:original,gradient_surface_endpoints:surfaces,gradient_boundaries:boundaries};
  });
  contrast.push({screen,viewport:page.viewportSize(),...scan});
  await fs.writeFile('docs/browser-contrast-results.json',JSON.stringify({
   scope:'Actual Chrome color-contrast rule on recorded synthetic keyboard journey. Incomplete checks require separate review; no full accessibility conformance claim.',scans:contrast},null,2));
  console.log(`Contrast ${screen}: ${scan.violations.length} actual violations; boundary violations ${scan.gradient_boundaries.map(item=>item.violations.length)}; boundary incomplete ${scan.gradient_boundaries.map(item=>item.incomplete.length)}`);
 }
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(/\/api\/(offer|voice\/warmup)/.test(r.url()))microphone.push(r.url())});
 page.on('dialog',async dialog=>{
  dialogs.push({type:dialog.type(),message:dialog.message()});
  await dialog.accept(dialog.type()==='prompt'?(dialog.message().startsWith('Correct')?'TTL only; corrected keyboard transcript.':'Please preserve the corrected context.'):undefined);
 });
 const button=name=>page.getByRole('button',{name,exact:true}).first();
 async function reach(locator){
  // Monaco's native EditContext is focusable but has no visible box of its own.
  await locator.waitFor({state:'attached'});
  for(let n=0;n<300;n++){
   if(await locator.evaluate(el=>el===document.activeElement))return;
   await page.keyboard.press('Tab');
  }
  throw new Error('Keyboard cannot reach '+await locator.evaluate(el=>el.outerHTML.slice(0,250)));
 }
 async function activate(name){
  const target=button(name);await target.waitFor({state:'attached'});await page.waitForFunction(el=>!el.disabled,await target.elementHandle());await reach(target);
  const actions={'Pause interview':'pause','Resume interview':'resume','Confirm and continue to next stage':'advance','Complete interview':'advance','Confirm hypothesis':'hypothesis','Confirm conclusion':'conclusion','Explicitly skip this stage':'skip','Set practice objective':'practice_objective','Request authored hint':'hint'};
  const action=actions[name];
  const response=action?page.waitForResponse(r=>r.url().endsWith('/actions')&&r.request().method()==='POST'&&r.request().postDataJSON()?.action===action):null;
  await page.keyboard.press('Enter');
  if(response){const result=await response;assert.ok(result.ok(),name+': '+await result.text());await page.waitForFunction(()=>!document.querySelector('.interview-top .back-link:disabled'))}
 }
 async function write(label,text){await reach(page.getByLabel(label,{exact:true}).first());await page.keyboard.press('ControlOrMeta+A');await page.keyboard.type(text)}
 async function check(label){const target=page.getByLabel(label);await reach(target);if(!await target.isChecked())await page.keyboard.press('Space')}
 async function focused(locator){assert.ok(await locator.evaluate(el=>el===document.activeElement),'Expected focused '+await locator.textContent())}
 async function stage(name){const heading=page.getByRole('heading',{name,exact:true});await heading.waitFor();await page.waitForFunction(el=>el===document.activeElement,await heading.elementHandle());await focused(heading);await auditContrast(name);console.log('Keyboard stage: '+name)}
 async function noOverflow(){const size=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));assert.equal(size.viewport,size.document);return size}
 try{
  await page.goto(base);
  await page.getByRole('heading',{name:'Practice the interview your resume starts.'}).waitFor();
  await auditContrast('Landing');
  await activate('See an example');await page.getByRole('dialog').waitFor();
  await auditContrast('Synthetic example dialog');
  await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
  await focused(button('See an example'));checks.push('sample_escape_restores_trigger');
  await activate('Skip to main content');await focused(page.getByRole('heading',{name:'Practice the interview your resume starts.'}));checks.push('skip_navigation');
  await activate('Settings');
  await stage('Your private practice space');
  await write('Owner key','synthetic-browser-acceptance-owner-key');await page.keyboard.press('Enter');
  await page.getByLabel('Allow provider requests that may incur charges').waitFor();
  await auditContrast('Provider settings');
  await activate('My interviews');await stage('Pick up where you left off.');
  await page.getByText('Loading history…').waitFor({state:'hidden'});
  while(await button('Delete interview').count()){
   const count=await page.getByRole('button',{name:'Delete interview',exact:true}).count();
   await activate('Delete interview');
   await page.waitForFunction(before=>document.querySelectorAll('.history-row').length<before,count);
  }
  await activate('Settings');
  await page.getByLabel('Allow provider requests that may incur charges').waitFor();
  await check('Allow provider requests that may incur charges');
  if(await button('Save provider settings').isEnabled()){
   await activate('Save provider settings');await page.getByText('Provider and model settings saved.').waitFor();
  }
  await activate('Test connection');await page.getByText('Provider passed the synthetic interview and structured-output checks.').waitFor();
  await activate('Prepare my interview');await stage('Let’s make this feel like your interview.');
  await write('Or paste resume text','Built a product API with Python and explicit cache invalidation.');
  await activate('Review pasted text');await page.getByLabel('Selected context to share').waitFor();
  await write('Your contribution','Built a product API; personally implemented cache invalidation.');
  await check('I confirm these edited claims and the selected resume context.');
  await check('I consent to this selected text and code being processed by the displayed provider and routes.');
  await activate('Start my interview');await page.getByLabel('Type your answer').waitFor();
  await write('Type your answer','TTL only');await activate('Send answer');
  await page.getByRole('heading',{name:'What happens if the record changes before the TTL expires?'}).waitFor();
  await auditContrast('Dialogue');
  await activate('Pause interview');await button('Resume interview').waitFor();
  assert.equal(await page.getByLabel('Type your answer').isDisabled(),true);
  await auditContrast('Paused dialogue');
  await activate('Resume interview');await button('Pause interview').waitFor();
  checks.push('keyboard_setup_claims_dialogue_pause_resume');
  await activate('Confirm and continue to next stage');await stage('Synthetic exercise: a stale price response');
  const card=page.getByRole('button',{name:/Request .*key trace/});await reach(card);await page.keyboard.press('Enter');
  await page.getByText('The reader looks up product:42:v7. The write invalidation deletes product:42.',{exact:true}).waitFor();
  await write('Provisional explanation or justified revision','Reader and invalidator use different keys.');await activate('Confirm hypothesis');
  await write('Conclusion and verification plan','Compare exact keys and verify read after write.');await activate('Confirm conclusion');
  await activate('Confirm and continue to next stage');await stage('Count normalized event names');
  const language=page.getByLabel('Language',{exact:true});await reach(language);await page.keyboard.press('Home');await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
  await page.locator('.view-lines').filter({hasText:'return 0;'}).waitFor();
  await page.keyboard.press('Home');await page.keyboard.press('Enter');
  await page.locator('.view-lines').filter({hasText:'def solve():'}).waitFor();
  const editor=page.getByRole('textbox',{name:/Code editor/});await reach(editor);
  await page.keyboard.press('ControlOrMeta+A');await page.keyboard.type("print('keyboard draft')");
  await page.keyboard.press('Tab');await focused(button('Run public examples'));
  await page.keyboard.press('Enter');
  await page.getByText('Dedicated Ubuntu runner is not configured. Code was saved; no code executed locally.').waitFor();
  await auditContrast('Coding outage');
  await noOverflow();await page.screenshot({path:'docs/screenshots/keyboard-coding-mobile.png',fullPage:true});
  await page.screenshot({path:'docs/screenshots/keyboard-coding-focus-mobile.png'});
  checks.push('keyboard_evidence_hypothesis_conclusion','stage_heading_focus','monaco_named_keyboard_edit_tab_exit','language_starters','unconfigured_runner_safe_failure');
  await activate('Explicitly skip this stage');await stage('Authored reference review');
  await write('Next practice objective','Compare request-level evidence with aggregate dashboards.');await activate('Set practice objective');
  await activate('Confirm and continue to next stage');await stage('Coached practice: compare evidence scopes');
  assert.equal(await page.getByLabel('Conclusion and verification plan',{exact:true}).inputValue(),'');
  await activate('Request authored hint');
  await activate('Confirm and continue to next stage');await stage('Fresh transfer exercise: a stale price response');
  assert.equal(await page.getByLabel('Provisional explanation or justified revision',{exact:true}).inputValue(),'');
  assert.equal(await page.getByLabel('Conclusion and verification plan',{exact:true}).inputValue(),'');
  assert.equal(await page.getByRole('button',{name:'Evidence and reasoning',exact:true}).getAttribute('aria-pressed'),'true');
  await write('Conclusion and verification plan','Trace the individual request and replica version before changing cache policy.');await activate('Confirm conclusion');
  await activate('Confirm and continue to next stage');await button('Complete interview').waitFor();await activate('Complete interview');
  await stage('Your practice, with the evidence attached.');
  const link=page.getByRole('link',{name:'Review candidate statements',exact:true}).first();await reach(link);await page.keyboard.press('Enter');
  await focused(page.locator('#review-transcript'));
  await activate('Correct transcript');await page.getByText('TTL only; corrected keyboard transcript.',{exact:true}).first().waitFor();
  const currentObservation=page.locator('.finding').filter({hasText:'TTL only; corrected keyboard transcript.'}).getByRole('button',{name:'Challenge observation',exact:true});
  await reach(currentObservation);await page.keyboard.press('Enter');
  await page.getByText('disputed',{exact:true}).first().waitFor();
  await auditContrast('Corrected and disputed report');
  checks.push('keyboard_review_objective_coaching_fresh_completion','new_exercise_reasoning_drafts_clear','task_workspace_compact_by_default','report_evidence_link_moves_focus','report_correction_and_dispute_native_dialogs');
  const mobile=await noOverflow();await page.screenshot({path:'docs/screenshots/keyboard-report-mobile.png',fullPage:true});
  await page.screenshot({path:'docs/screenshots/keyboard-report-focus-mobile.png'});
  await page.setViewportSize({width:1440,height:1000});const desktop=await noOverflow();
  await auditContrast('Report desktop');
  await page.screenshot({path:'docs/screenshots/keyboard-report-focus-desktop.png'});
  await page.screenshot({path:'docs/screenshots/keyboard-report-desktop.png',fullPage:true});
  await activate('Back to My interviews');await stage('Pick up where you left off.');
  await activate('Delete interview');await page.getByText('No saved interviews.',{exact:true}).waitFor();await focused(page.getByRole('heading',{name:'Pick up where you left off.'}));checks.push('keyboard_history_delete_native_confirmation');
  assert.deepEqual(errors,[]);assert.deepEqual(microphone,[]);
  const result={provider:'synthetic browser harness',runner:'unconfigured; no candidate execution',checks,mobile,desktop,native_dialogs:dialogs,errors,microphone_calls:microphone,
   scope:'Chrome keyboard input for web controls, Monaco and links. Browser-native prompt/confirm responses use Playwright dialog automation. No screen-reader, physical microphone, real provider or dedicated-host claim.'};
  await fs.writeFile('docs/browser-keyboard-journey-results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  assert.equal(contrast.reduce((count,scan)=>count+scan.violations.length+scan.gradient_boundaries.reduce((sum,item)=>sum+item.violations.length,0),0),0,'Rendered text contrast violations; see docs/browser-contrast-results.json');
 }catch(error){await page.screenshot({path:'docs/screenshots/keyboard-failure.png',fullPage:true});console.error('Focused element:',await page.evaluate(()=>document.activeElement?.outerHTML.slice(0,500)));throw error}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
