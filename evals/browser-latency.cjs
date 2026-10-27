// Actual browser/Opus/VAD/Whisper/Kokoro. Synthetic microphone; cloud is synthetic
// unless an explicitly approved real provider is selected by the operator.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const realProvider=process.env.FIELDNOTE_REAL_PROVIDER;
assert.ok(!realProvider||['groq','openrouter'].includes(realProvider));
const resultPath=process.env.FIELDNOTE_LATENCY_RESULT_PATH||
 (realProvider?'docs/browser-real-provider-latency-results.json':'docs/browser-latency-results.json');

function distribution(values){
  const sorted=[...values].sort((a,b)=>a-b);
  const percentile=p=>{const index=(sorted.length-1)*p,low=Math.floor(index),high=Math.ceil(index);return sorted[low]+(sorted[high]-sorted[low])*(index-low)};
  return {count:values.length,p50_seconds:percentile(.5),p95_seconds:percentile(.95),minimum_seconds:sorted[0],maximum_seconds:sorted.at(-1),method:'linear interpolation, (n-1)*p'};
}

(async()=>{
  const fixture=(await fs.readFile('data/browser-synthetic-microphone.wav')).toString('base64');
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,
    args:['--autoplay-policy=no-user-gesture-required']});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.addInitScript(()=>{
    window.acceptancePlayback=[];
    const originalSend=RTCDataChannel.prototype.send;
    RTCDataChannel.prototype.send=function(data){
      if(typeof data==='string'){
        try{const message=JSON.parse(data);if(message.type==='playback_started')window.acceptancePlayback.push(message)}catch{}
      }
      return originalSend.call(this,data);
    };
    navigator.mediaDevices.getUserMedia=async()=>{
      const ac=new AudioContext();await ac.resume();
      const destination=ac.createMediaStreamDestination(),zero=ac.createConstantSource();
      zero.offset.value=0;zero.connect(destination);zero.start();
      window.acceptanceMicrophone={ac,destination,zero};return destination.stream;
    };
    const original=RTCPeerConnection.prototype.createDataChannel;
    RTCPeerConnection.prototype.createDataChannel=function(...args){
      const channel=original.apply(this,args);window.acceptanceChannel=channel;return channel;
    };
  });
  const page=await context.newPage(),base=realProvider?'http://localhost:8000':'http://127.0.0.1:8001';
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const result={status:'running',real_browser_webrtc:true,real_local_models:true,
    synthetic_microphone:true,synthetic_cloud:!realProvider,real_provider:realProvider||null,physical_microphone:false,
    speech_end_basis:'scheduled end of a local synthetic Web Audio source, not physical speech end',
    latency_clock:'browser performance.timeOrigin + performance.now; no server/client clock subtraction',
    server_marker_clock:'server Unix seconds; speech end is VAD endpoint minus configured silence',
    measurement_wait:'Native browser playback marker; no session polling during inference',state_poll_interval_ms:500,
    environment:'Windows Chrome; WSL Ubuntu; CUDA Whisper large-v3-turbo int8_float16 on RTX 4050 6 GiB; CPU Kokoro af_heart',
    targets:{p50_seconds:2,p95_seconds:4},samples:[],errors};
  let sid,headers;
  const state=async()=>{const response=await context.request.get(`${base}/api/sessions/${sid}`);assert.equal(response.status(),200);return response.json()};
  async function until(predicate,label,timeout=30000){
    const deadline=Date.now()+timeout;
    while(Date.now()<deadline){const s=await state();if(s.last_error)throw new Error(JSON.stringify(s.last_error));if(predicate(s))return s;await page.waitForTimeout(500)}
    throw new Error(`Timed out: ${label}`);
  }
  try{
    await page.goto(base);
    const login=await context.request.post(base+'/api/auth',{data:{token:realProvider?
      (await fs.readFile('data/owner.key','utf8')).trim():'synthetic-browser-acceptance-owner-key'}});
    headers={'X-CSRF-Token':(await login.json()).csrf_token};
    const settings=await(await context.request.get(base+'/api/settings')).json();
    if(realProvider){
      assert.equal(settings.provider,realProvider,'Select and validate the approved configuration before running');
      assert.equal((await(await context.request.get(base+'/api/readiness')).json()).providers[realProvider].validated,true);
      result.configuration=settings.providers[realProvider];
    }else{
      settings.provider='groq';settings.providers.groq.paid_opt_in=true;
      assert.equal((await context.request.patch(base+'/api/settings',{headers,data:settings})).status(),200);
      assert.equal((await context.request.post(base+'/api/providers/groq/test',{headers,data:settings.providers.groq})).status(),200);
    }
    const created=await context.request.post(base+'/api/sessions',{headers,data:{
      context:'Synthetic practice: implemented cache invalidation for a product API.',
      claims:[{source_bullet:'Implemented cache invalidation.',contribution:'Implemented write invalidation.'}],
      role:'backend',experience:'junior',language:'python',duration_minutes:25,
      cloud_consent:true,record_audio:false,retention:'30_days',idempotency_key:'latency-'+Date.now()}});
    assert.equal(created.status(),200,await created.text());sid=(await created.json()).id;
    await page.reload();await page.getByRole('button',{name:'My interviews',exact:true}).click();
    await page.getByRole('button',{name:'Resume interview',exact:true}).first().click();
    await page.locator('.interview-screen').waitFor();
    await until(s=>s.turns.at(-1)?.role==='assistant'&&s.turns.at(-1)?.delivery==='complete','initial text question');
    const enableStarted=Date.now();
    result.models_preloaded_before_enable=(await(await context.request.get(base+'/api/readiness')).json()).voice.ready;
    await page.getByRole('button',{name:'Enable local voice',exact:true}).click();
    await page.getByRole('button',{name:'Disconnect microphone',exact:true}).waitFor({timeout:150000});
    await page.waitForFunction(()=>window.acceptanceChannel?.readyState==='open');
    result.voice_enable_seconds=(Date.now()-enableStarted)/1000;
    result.recorded_process_model_warmup_seconds=(await(await context.request.get(base+'/api/readiness')).json()).voice.warmup_seconds;
    for(let index=0;index<(realProvider?3:10);index++){
      if(index)await until(s=>s.turns.at(-1)?.speech_delivery?.status==='estimated_complete','previous audio estimated complete');
      const before=await state(),priorUsers=before.turns.filter(t=>t.role==='user').length;
      const playedBefore=await page.evaluate(()=>window.acceptancePlayback.length);
      const input=await page.evaluate(async data=>{
        const {ac,destination}=window.acceptanceMicrophone;
        const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));
        const buffer=await ac.decodeAudioData(bytes.buffer),source=ac.createBufferSource();
        source.buffer=buffer;source.connect(destination);
        const started=performance.timeOrigin+performance.now();source.start();
        return {started_client_ms:started,ended_client_ms:started+buffer.duration*1000,duration_seconds:buffer.duration};
      },fixture);
      await page.waitForFunction(count=>window.acceptancePlayback.length>count,playedBefore,{timeout:30000});
      // Playback may precede provider completion. Wait for persisted request
      // metadata as well; latency still uses the original browser playback
      // timestamp, never the later polling/observation time.
      const current=await until(s=>s.turns.filter(t=>t.role==='user').length>priorUsers&&
        s.turns.at(-1)?.role==='assistant'&&s.turns.at(-1)?.generation_id===s.generation_id&&
        s.turns.at(-1)?.speech_delivery?.timing?.first_playback_client_ms&&
        typeof s.turns.at(-1)?.timing?.first_usable_content==='number','meaningful browser playback and finalized request metadata');
      const answer=current.turns.filter(t=>t.role==='user').at(-1),question=current.turns.at(-1);
      const server=answer.speech_metadata?.timing,delivery=question.speech_delivery,timing=delivery.timing;
      for(const name of ['endpoint_decision','speech_end_estimate','stt_started','stt_completed'])assert.equal(typeof server?.[name],'number',name);
      for(const name of ['first_text_received_client_ms','first_text_displayed_client_ms','first_tts_clause_server','first_tts_chunk_server','first_audio_admitted_server','first_playback_client_ms'])assert.equal(typeof timing[name],'number',name);
      assert.equal(typeof question.timing?.request_started,'number');
      assert.equal(typeof question.timing?.first_usable_content,'number');
      const seconds=(timing.first_playback_client_ms-input.ended_client_ms)/1000;
      assert.ok(seconds>=0&&seconds<30);
      result.samples.push({sample:index+1,model_state:index?'subsequent_warm_turn':result.models_preloaded_before_enable?'first_measured_turn_in_warm_process':'first_turn_after_model_warmup',
        input,transcript:answer.text,generation_id:question.generation_id,
        speech_to_playback_seconds:seconds,
        speech_to_text_received_seconds:(timing.first_text_received_client_ms-input.ended_client_ms)/1000,
        server_stt_seconds:server.stt_completed-server.stt_started,
        server_provider_first_content_seconds:question.timing.first_usable_content-question.timing.request_started,
        server_tts_first_chunk_seconds:timing.first_tts_chunk_server-timing.first_tts_clause_server,
        server_speech_markers:server,server_request_markers:question.timing,delivery_markers:timing});
      await fs.writeFile(resultPath,JSON.stringify(result,null,2));
      console.log(JSON.stringify({sample:index+1,speech_to_playback_seconds:seconds}));
    }
    result.all_turns=distribution(result.samples.map(s=>s.speech_to_playback_seconds));
    result.subsequent_warm_turns=distribution(result.samples.slice(1).map(s=>s.speech_to_playback_seconds));
    result.first_turn_after_warmup_seconds=result.samples[0].speech_to_playback_seconds;
    result.meets_timing_target=result.all_turns.p50_seconds<=2&&result.all_turns.p95_seconds<=4;
    if(!realProvider)result.meets_synthetic_target=result.meets_timing_target;
    result.status=realProvider?(result.meets_timing_target?'measured_real_provider_target_met':'measured_real_provider_target_missed'):
      result.meets_timing_target?'measured_synthetic_target_met':'measured_synthetic_target_missed';
    result.real_provider_latency_status=realProvider?
      'Measured with the configured real provider and local models, synthetic browser microphone only; three samples are diagnostic, not physical microphone acceptance.':
      'unavailable; synthetic cloud response is not provider connectivity or production latency';
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({status:result.status,all_turns:result.all_turns,subsequent_warm_turns:result.subsequent_warm_turns}));
  }catch(error){result.status='failed';result.failure=error.message;throw error}
  finally{
    await fs.writeFile(resultPath,JSON.stringify(result,null,2));
    if(sid&&headers)await context.request.delete(`${base}/api/sessions/${sid}`,{headers});
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exit(1)});
