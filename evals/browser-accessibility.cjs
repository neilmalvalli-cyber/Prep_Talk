// Focused keyboard/motion acceptance; not a full screen-reader conformance audit.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
 const page=await browser.newPage({viewport:{width:360,height:800},reducedMotion:'reduce'});
 const base=process.env.FIELDNOTE_TEST_ORIGIN||'http://127.0.0.1:8002';
 const errors=[],cloud=[],microphone=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.url().includes('/api/offer')||r.url().includes('/api/voice/warmup'))microphone.push(r.url());if(r.url().includes('/test'))cloud.push(r.url())});
 async function activate(name){
  for(let n=0;n<150;n++){
   const found=await page.evaluate(label=>{
    const active=document.activeElement;
    return active?.tagName==='BUTTON'&&(active.textContent?.trim()===label||active.getAttribute('aria-label')===label);
   },name);
   if(found){await page.keyboard.press('Enter');return}
   await page.keyboard.press('Tab');
  }
  throw new Error('Keyboard could not reach '+name);
 }
 try{
  await page.goto(base);
  await page.getByRole('heading',{name:'Practice the interview your resume starts.'}).waitFor();
  await activate('See an example');
  await page.getByRole('dialog').waitFor();
  const focusedInDialog=await page.evaluate(()=>!!document.activeElement?.closest('[role="dialog"]'));
  assert.ok(focusedInDialog);
  for(let i=0;i<8;i++){
   await page.keyboard.press('Tab');
   assert.ok(await page.evaluate(()=>!!document.activeElement?.closest('[role="dialog"]')));
  }
  await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({state:'hidden'});
  await activate('My interviews');
  await page.getByLabel('Owner key').waitFor();
  for(let i=0;i<30;i++){
   if(await page.evaluate(()=>document.activeElement?.getAttribute('type')==='password'))break;
   await page.keyboard.press('Tab');
  }
  assert.equal(await page.evaluate(()=>document.activeElement?.getAttribute('type')),'password');
  await page.keyboard.type('synthetic-browser-acceptance-owner-key');
  await page.keyboard.press('Enter');
  await page.getByRole('heading',{name:'Pick up where you left off.'}).waitFor();
  await activate('Settings');
  await page.getByRole('combobox').first().waitFor();
  const overflow=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  assert.equal(overflow.viewport,overflow.document);
  await activate('Prepare my interview');
  await page.getByLabel('Or paste resume text').waitFor();
  const animated=await page.evaluate(()=>Array.from(document.querySelectorAll('.sphere-wrap *')).some(el=>{
   const css=getComputedStyle(el);return css.animationName!=='none'&&css.animationDuration.split(',').some(v=>parseFloat(v)>.01);
  }));
  assert.equal(animated,false);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.evaluate(()=>{
   Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
   document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.locator('.page-hidden .sphere').first().waitFor();
  const hiddenAnimations=await page.evaluate(()=>Array.from(document.querySelectorAll('.page-hidden .sphere')).every(el=>
   getComputedStyle(el).animationPlayState==='paused'&&getComputedStyle(el,'::before').animationPlayState==='paused'&&
   Array.from(el.querySelectorAll('i')).every(child=>getComputedStyle(child).animationPlayState==='paused')));
  assert.ok(hiddenAnimations);
  await page.evaluate(()=>{
   delete document.hidden;
   document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.locator('.page-hidden').waitFor({state:'detached'});
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.deepEqual(microphone,[]);assert.deepEqual(cloud,[]);assert.deepEqual(errors,[]);
  const result={keyboard_landing_example_escape:true,dialog_focus_trapped:true,keyboard_owner_signin:true,
   keyboard_settings_and_setup:true,reduced_motion_sphere_static:true,mobile_overflow:overflow,
   injected_visibility_pauses_sphere_and_pseudo_element:true,visible_restores_sphere:true,
   microphone_calls:microphone,cloud_test_calls:cloud,errors,
   scope:'Focused Chrome keyboard/reduced-motion checks; full screen-reader and complete keyboard interview audit remain separate.'};
  await fs.writeFile('docs/browser-accessibility-results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
