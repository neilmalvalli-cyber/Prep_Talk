// Real Chrome/WebRTC/local-model acceptance. Cloud responses and mic source are synthetic.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE);
const fs = require('node:fs/promises');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROME_EXECUTABLE,
    args:['--autoplay-policy=no-user-gesture-required']});
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  // Replace only microphone acquisition. The application still uses actual browser
  // Web Audio, RTCPeerConnection, Opus, transport, VAD, Whisper and Kokoro.
  await context.addInitScript(() => {
    window.acceptanceAnimationFrames=0;
    const nativeFrame=window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame=callback=>nativeFrame(now=>{window.acceptanceAnimationFrames++;callback(now)});
    let hidden=false;
    Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
    window.acceptanceSetHidden=value=>{hidden=value;document.dispatchEvent(new Event('visibilitychange'))};
    window.acceptanceContexts=[];
    const OriginalContext=window.AudioContext;
    window.AudioContext=class extends OriginalContext{constructor(...args){super(...args);window.acceptanceContexts.push(this)}};
    window.acceptancePeers=[];
    const OriginalPeer=window.RTCPeerConnection;
    window.RTCPeerConnection=class extends OriginalPeer{constructor(...args){super(...args);window.acceptancePeers.push(this)}};
    window.acceptanceDropAcks=false;
    const originalSend=RTCDataChannel.prototype.send;
    RTCDataChannel.prototype.send=function(data){
      if(window.acceptanceDropAcks&&typeof data==='string'){
        try{if(JSON.parse(data).type==='playback_ack')return;}catch{}
      }
      return originalSend.call(this,data);
    };
    window.acceptanceMicAcquisitions=0;
    navigator.mediaDevices.getUserMedia = async () => {
      window.acceptanceMicAcquisitions++;
      const ac = new AudioContext();
      await ac.resume();
      const destination = ac.createMediaStreamDestination();
      const constant = ac.createConstantSource();
      constant.offset.value = 0;
      constant.connect(destination); constant.start();
      window.acceptanceMicrophone = {ac, destination, constant};
      return destination.stream;
    };
    const OriginalAudio = window.Audio;
    window.acceptanceOutputs = [];
    window.Audio = function(...args) {
      const audio = new OriginalAudio(...args);
      window.acceptanceOutputs.push(audio);
      return audio;
    };
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const base = 'http://127.0.0.1:8001';
  let sid;
  let headers;
  let ttsFault=false;
  const state = async () => (await context.request.get(`${base}/api/sessions/${sid}`)).json();
  async function waitState(predicate, label, timeout=20000) {
    const until = Date.now()+timeout;
    while (Date.now()<until) {
      const value = await state();
      if (predicate(value)) return value;
      await page.waitForTimeout(100);
    }
    throw new Error(`Timed out: ${label}`);
  }
  try {
    await page.goto(base);
    const login = await context.request.post(base+'/api/auth', {data:{token:'synthetic-browser-acceptance-owner-key'}});
    headers = {'X-CSRF-Token':(await login.json()).csrf_token};
    const settings = await (await context.request.get(base+'/api/settings')).json();
    settings.provider='groq'; settings.providers.groq.paid_opt_in=true;
    assert.equal((await context.request.patch(base+'/api/settings',{headers,data:settings})).status(),200);
    assert.equal((await context.request.post(base+'/api/providers/groq/test',{headers,data:settings.providers.groq})).status(),200);
    for (const old of (await (await context.request.get(base+'/api/sessions')).json()).sessions)
      await context.request.delete(base+'/api/sessions/'+old.id,{headers});
    const created = await context.request.post(base+'/api/sessions',{headers,data:{
      context:'Built a cache-backed product API.',
      claims:[{source_bullet:'Built a cache-backed product API.',contribution:'Implemented cache invalidation.'}],
      role:'backend',experience:'junior',language:'python',duration_minutes:15,
      cloud_consent:true,record_audio:false,retention:'30_days',idempotency_key:'voice-recovery-'+Date.now()}});
    assert.equal(created.status(),200,await created.text()); sid=(await created.json()).id;
    await page.reload();
    await page.getByRole('button',{name:'My interviews',exact:true}).click();
    await page.getByRole('button',{name:'Resume interview',exact:true}).first().click();
    await page.locator('.interview-screen').waitFor();
    await waitState(s=>s.turns.some(t=>t.role==='assistant'&&t.delivery==='complete'),'first question');
    const warm=await context.request.post(`${base}/api/voice/warmup`,{headers,timeout:150000});
    assert.equal(warm.status(),200);assert.equal((await warm.json()).ready,true);
    const rejectedOffers=[];
    for(const sdp of ['not-an-sdp','v=0\r\n','v=0\r\nm=audio bogus RTP/AVP 111\r\n']){
      const response=await context.request.post(`${base}/api/offer`,{headers,data:{session_id:sid,sdp,type:'offer'}});
      assert.ok([422,503].includes(response.status()),'Malformed native offer returned '+response.status());
      const channel=await(await context.request.get(`${base}/api/acceptance/voice/${sid}`)).json();
      assert.equal(channel.voice_generation,null);assert.equal(channel.pipeline,'missing');
      rejectedOffers.push({status:response.status(),initialization_released:true});
    }
    await page.getByRole('button',{name:'Enable local voice',exact:true}).click();
    await page.getByRole('button',{name:'Disconnect microphone',exact:true}).waitFor({timeout:150000});
    await page.evaluate(()=>window.acceptanceMicrophone.destination.stream.getAudioTracks().forEach(track=>track.enabled=false));
    await page.locator('.sphere-muted').waitFor({timeout:5000});
    assert.equal(await page.locator('.sphere-listening').count(),0);
    await page.evaluate(()=>window.acceptanceMicrophone.destination.stream.getAudioTracks().forEach(track=>track.enabled=true));
    await page.locator('.sphere-listening').waitFor({timeout:5000});
    await page.evaluate(()=>window.acceptanceSetHidden(true));
    await page.locator('.page-hidden').waitFor();
    assert.ok(await page.evaluate(()=>Array.from(document.querySelectorAll('.page-hidden .sphere, .page-hidden .sphere i')).every(el=>getComputedStyle(el).animationPlayState==='paused')&&Array.from(document.querySelectorAll('.page-hidden .sphere')).every(el=>getComputedStyle(el,'::before').animationPlayState==='paused')));
    const hiddenFrames=await page.evaluate(()=>window.acceptanceAnimationFrames);
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(()=>window.acceptanceAnimationFrames),hiddenFrames,'hidden page continued the visual RAF loop');
    await page.evaluate(()=>window.acceptanceSetHidden(false));
    await page.waitForFunction(before=>window.acceptanceAnimationFrames>before,hiddenFrames);
    assert.equal(await page.locator('.page-hidden').count(),0);
    const stops=[];
    for(let index=0;index<3;index++) {
      await page.getByRole('button',{name:'Repeat question',exact:true}).click();
      await page.locator('.sphere-speaking').waitFor({timeout:30000});
      const before=await state();
      const start=Date.now();
      await page.getByRole('button',{name:'Stop',exact:true}).click();
      await page.waitForFunction(()=>window.acceptanceOutputs.every(audio=>audio.paused||audio.muted));
      const stopped=Date.now()-start;
      await waitState(s=>s.generation_id!==before.generation_id,'Stop generation invalidation');
      await page.waitForTimeout(1000);
      assert.equal(await page.locator('.sphere-speaking').count(),0,'stale speaking after Stop');
      stops.push(stopped);
    }
    console.log(JSON.stringify({repeated_stops_ms:stops}));
    await page.evaluate(()=>window.acceptanceDropAcks=true);
    await page.getByRole('button',{name:'Repeat question',exact:true}).click();
    await page.locator('.sphere-speaking').waitFor({timeout:30000});
    await page.waitForTimeout(1800);
    const stalled=await(await context.request.get(`${base}/api/acceptance/voice/${sid}`)).json();
    assert.ok(stalled.pending_audio_ms<=1001&&stalled.pending_audio_ms>=900,'slow client exceeded or did not fill the audio window');
    assert.ok(stalled.offered_audio_ms<=stalled.generated_audio_ms+21,'audio accumulated before the backpressure guard');
    assert.ok(stalled.peak_pending_audio_ms<=1001,'audio window peak exceeded one second');
    await page.evaluate(()=>window.acceptanceDropAcks=false);
    await page.locator('.sphere-speaking').waitFor({timeout:10000});
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    // Speak while the interviewer is actually playing, exercising VAD barge-in.
    await page.getByRole('button',{name:'Repeat question',exact:true}).click();
    await page.locator('.sphere-speaking').waitFor({timeout:30000});
    const beforeSpeech=await state();
    const wav=(await fs.readFile('data/browser-synthetic-microphone.wav')).toString('base64');
    await page.evaluate(async data => {
      const {ac,destination}=window.acceptanceMicrophone;
      const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));
      const buffer=await ac.decodeAudioData(bytes.buffer);
      const source=ac.createBufferSource();source.buffer=buffer;source.connect(destination);source.start();
    }, wav);
    const spoken=await waitState(s=>s.turns.some(t=>t.role==='user'&&t.input_source==='local_speech'), 'real browser upstream STT',30000);
    const utterance=spoken.turns.find(t=>t.role==='user'&&t.input_source==='local_speech');
    // Opus/VAD/STT may mishear the technical homophone. Preserve the measured
    // transcript and exercise explicit correction rather than silently replacing it.
    assert.match(utterance.text,/invalidated the (cache|cash) after the write/i);
    assert.notEqual(spoken.generation_id,beforeSpeech.generation_id);
    await waitState(s=>s.turns.some(t=>t.role==='assistant'&&t.text.includes('failed invalidation')&&t.delivery==='complete'),'answer-dependent follow-up');
    page.once('dialog',dialog=>dialog.accept('I invalidated the cache after the write.'));
    await page.getByRole('button',{name:'Correct transcript',exact:true}).first().click();
    const corrected=await waitState(s=>s.turns.some(t=>t.id===utterance.id&&t.version===2),'speech transcript correction');
    const repaired=corrected.turns.find(t=>t.id===utterance.id);
    assert.equal(repaired.versions[0].text,utterance.text);
    assert.equal(repaired.versions[1].kind,'candidate_correction');
    assert.equal(repaired.input_source,'local_speech');
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    await page.reload();
    const paused=await waitState(s=>s.paused,'reload pauses authoritative session');
    const turnCount=paused.turns.length;
    await page.getByRole('button',{name:'My interviews',exact:true}).click();
    await page.getByRole('button',{name:'Resume interview',exact:true}).first().click();
    await page.locator('.interview-screen').waitFor();
    await page.getByRole('button',{name:'Resume interview',exact:true}).click();
    await page.getByRole('button',{name:'Enable local voice',exact:true}).click();
    await page.getByRole('button',{name:'Disconnect microphone',exact:true}).waitFor({timeout:30000});
    await page.waitForTimeout(1500);
    assert.equal((await state()).turns.length,turnCount,'reconnect must not duplicate questions');
    assert.equal(await page.locator('.sphere-speaking').count(),0,'reconnect must not replay audio');
    assert.equal((await context.request.post(`${base}/api/acceptance/voice/${sid}/fail-tts`,{headers})).status(),200);
    ttsFault=true;
    await page.getByRole('button',{name:'Repeat question',exact:true}).click();
    await page.getByText('Local speech synthesis failed. Continue with the displayed text; reconnect voice to retry speech.',{exact:true}).waitFor({timeout:20000});
    await page.waitForFunction(()=>window.acceptanceOutputs.every(audio=>audio.paused||audio.muted));
    await page.screenshot({path:'docs/screenshots/browser-voice-tts-failure.png',fullPage:true});
    await page.getByLabel('Type your answer',{exact:true}).fill('I saved the write and retried invalidation from a durable queue.');
    await page.getByRole('button',{name:'Send answer',exact:true}).click();
    await waitState(s=>s.turns.some(t=>t.role==='user'&&t.text.includes('durable queue')),'typed continuation after TTS failure');
    assert.equal((await context.request.post(`${base}/api/acceptance/voice/${sid}/restore-tts`,{headers})).status(),200);
    ttsFault=false;
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    const beforeLimit=await state();
    const userCount=beforeLimit.turns.filter(t=>t.role==='user').length;
    assert.equal((await context.request.post(`${base}/api/acceptance/voice/${sid}/fill-held-draft`,{headers})).status(),200);
    await page.evaluate(async data=>{
      const {ac,destination}=window.acceptanceMicrophone;
      const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));
      const source=ac.createBufferSource();source.buffer=await ac.decodeAudioData(bytes.buffer);
      source.connect(destination);source.start();
    },wav);
    const limited=await waitState(s=>s.paused&&s.draft_answer?.length===12000,'voice input limit preserves bounded draft',30000);
    assert.equal(limited.turns.filter(t=>t.role==='user').length,userCount,'input failure submitted a partial answer');
    assert.equal(limited.last_error.code,'voice_input_limit');
    await page.getByRole('button',{name:'Enable local voice',exact:true}).waitFor({timeout:15000});
    await page.getByRole('button',{name:'Resume interview',exact:true}).click();
    await page.getByLabel('Type your answer',{exact:true}).fill('My reviewed shorter draft.');
    await page.getByRole('button',{name:'Send answer',exact:true}).click();
    await waitState(s=>s.turns.some(t=>t.role==='user'&&t.text==='My reviewed shorter draft.')&&s.turns.at(-1)?.delivery==='complete','reviewed draft submitted once');
    await page.getByRole('button',{name:'Enable local voice',exact:true}).click();
    await page.getByRole('button',{name:'Disconnect microphone',exact:true}).waitFor({timeout:30000});
    await page.evaluate(()=>{
      window.acceptanceLostContext=window.acceptanceContexts.at(-1);
      const peer=window.acceptancePeers.at(-1);peer.close();
      peer.dispatchEvent(new Event('connectionstatechange'));
    });
    await page.waitForFunction(()=>window.acceptanceLostContext.state==='closed');
    await waitState(s=>s.paused,'peer loss pauses authoritative session');
    await page.waitForFunction(()=>{const resume=document.querySelector('.interview-top .back-link');return resume&&!resume.disabled});
    const lostVoice=await(await context.request.get(`${base}/api/acceptance/voice/${sid}`)).json();
    assert.equal(lostVoice.connected,false);
    assert.equal(lostVoice.pipeline,'missing','server pipeline must be released before Resume becomes available');
    const closedFrames=await page.evaluate(()=>window.acceptanceAnimationFrames);
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(()=>window.acceptanceAnimationFrames),closedFrames,'lost connection kept the visual loop');
    await page.getByRole('button',{name:'Resume interview',exact:true}).click();
    await page.getByRole('button',{name:'Enable local voice',exact:true}).click();
    await page.getByRole('button',{name:'Disconnect microphone',exact:true}).waitFor({timeout:30000});
    await page.getByRole('button',{name:'Disconnect microphone',exact:true}).click();
    await waitState(s=>s.paused,'media-only disconnect pauses authoritative session');
    await page.getByRole('button',{name:'Resume interview',exact:true}).click();
    await waitState(s=>!s.paused,'explicit resume after media disconnect');
    // Leaving the screen during model warmup must not acquire a mic later.
    const acquiredBefore=await page.evaluate(()=>window.acceptanceMicAcquisitions);
    let releaseWarmup,observedWarmup;
    const release=new Promise(resolve=>releaseWarmup=resolve);
    const observed=new Promise(resolve=>observedWarmup=resolve);
    await page.route('**/api/voice/warmup',async route=>{
      observedWarmup();await release;
      await route.fulfill({json:{ready:true,detail:'Synthetic delayed warmup response'}});
    });
    await page.getByRole('button',{name:'Enable local voice',exact:true}).click();
    await observed;
    await page.getByRole('button',{name:'My interviews',exact:true}).click();
    releaseWarmup();
    await page.waitForTimeout(500);
    assert.equal(await page.evaluate(()=>window.acceptanceMicAcquisitions),acquiredBefore,'abandoned warmup acquired a microphone');
    await page.unroute('**/api/voice/warmup');
    const result={real_browser_webrtc:true,real_local_models:true,synthetic_cloud:true,
      synthetic_browser_microphone:true,repeated_stop_to_muted_or_paused_ms:stops,
      real_browser_upstream_transcript:utterance.text,explicit_speech_correction:true,vad_barge_in:true,
      slow_client_audio_pending_ms:stalled.pending_audio_ms,
      slow_client_offered_ahead_ms:stalled.offered_audio_ms-stalled.generated_audio_ms,
      slow_client_resumes_without_repeat:true,
      reload_pauses_session:true,reconnect_no_replay_or_duplicate:true,
      injected_tts_failure_retains_typed_path:true,media_only_disconnect_pauses:true,
      injected_visibility_pauses_css_and_visual_raf:true,visible_resumes_visual_loop:true,
      native_peer_close_with_injected_state_event_releases_audio_context_and_visual_loop:true,
      peer_loss_http_disconnect_releases_server_pipeline_before_resume:true,
      malformed_native_offers:rejectedOffers,
      abandoned_warmup_no_microphone:true,errors};
    result.injected_held_draft_limit_preserves_text_without_partial_answer=true;
    result.disabled_microphone_never_appears_listening=true;
    assert.deepEqual(errors,[]);
    await fs.writeFile('docs/browser-voice-recovery-results.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } catch(error) {
    console.error(JSON.stringify({visible_errors:await page.locator('[role="alert"]').allTextContents(),
      voice: sid ? await(await context.request.get(`${base}/api/acceptance/voice/${sid}`)).json() : null}));
    await page.screenshot({path:'docs/screenshots/browser-voice-recovery-failure.png',fullPage:true});
    throw error;
  } finally {
    if(ttsFault&&sid&&headers) await context.request.post(`${base}/api/acceptance/voice/${sid}/restore-tts`,{headers});
    if(sid&&headers) await context.request.delete(`${base}/api/sessions/${sid}`,{headers});
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exit(1)});
