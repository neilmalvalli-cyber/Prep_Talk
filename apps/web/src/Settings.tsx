import { useEffect, useMemo, useState } from 'react'
import { Check, CircleHelp, LoaderCircle, RefreshCw, Save, Settings2, ShieldCheck, TriangleAlert } from 'lucide-react'
import { api, errorMessage, type AppSettings, type Model, type Provider, type ProviderConfig, type Readiness } from './api'

type Route = { provider_name?: string; tag?: string; provider_tag?: string; supported_parameters?: string[]; pricing?: unknown }
type RouteChoice = { id: string; name: string; pricing?: unknown; supported_parameters: string[] }
type SettingsProps = { settings: AppSettings; onSave: (settings: AppSettings) => Promise<void>; onError: (message: string) => void; onMessage: (message: string) => void }

const routeId = (route: Route) => route.provider_name || route.tag || route.provider_tag || ''
const formatPricing = (value: unknown):string => {
  if(value==null)return 'Pricing unavailable'
  if(typeof value==='string')return value
  if(typeof value!=='object')return String(value)
  const rates=value as Record<string,unknown>
  const price=(rate:unknown)=>{const number=Number(rate);return rate==null||rate===''||!Number.isFinite(number)?'unknown':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:3}).format(number*1_000_000)}
  if('prompt' in rates||'completion' in rates)return `${price(rates.prompt)} input / ${price(rates.completion)} output per 1M tokens`
  return Object.entries(rates).map(([key,rate])=>`${key.replaceAll('_',' ')}: ${String(rate)}`).join('; ')||'Pricing unavailable'
}

export default function Settings({ settings, onSave, onError, onMessage }: SettingsProps) {
  const [draft, setDraft] = useState<AppSettings>(settings)
  const [models, setModels] = useState<Model[]>([])
  const [liveRoutes, setLiveRoutes] = useState<RouteChoice[]>([])
  const [assessmentRoutes, setAssessmentRoutes] = useState<RouteChoice[]>([])
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [loadingCatalog, setLoadingCatalog] = useState(false)
  const [loadingRoutes, setLoadingRoutes] = useState(false)
  const [loadingReadiness, setLoadingReadiness] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [loadError, setLoadError] = useState('')
  const provider = draft.provider
  const config = draft.providers[provider]
  const liveModel = models.find(model => model.id === config.live_model)
  const assessmentModel = models.find(model => model.id === config.assessment_model)
  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)
  const providerReady = readiness?.providers[provider]
  const providerName = provider === 'codex' ? 'OpenAI' : provider === 'groq' ? 'Groq' : 'OpenRouter'
  const pricingDisclosure = useMemo(() => {
    const liveRoute = liveRoutes.find(route => route.id === config.live_route)
    const reviewRoute = assessmentRoutes.find(route => route.id === config.assessment_route)
    return [
      `Interview model ${config.live_model || '(not selected)'}: ${formatPricing(liveModel?.pricing)}`,
      `Interview route ${config.live_route || '(not selected)'}: ${formatPricing(liveRoute?.pricing)}`,
      `Review model ${config.assessment_model || '(not selected)'}: ${formatPricing(assessmentModel?.pricing)}`,
      `Assessment route ${config.assessment_route || '(not selected)'}: ${formatPricing(reviewRoute?.pricing)}`,
    ].join('\n')
  }, [assessmentModel?.pricing, assessmentRoutes, config.assessment_model, config.assessment_route, config.live_model, config.live_route, liveModel?.pricing, liveRoutes])

  useEffect(() => { setDraft(settings) }, [settings])

  useEffect(() => {
    let active = true
    setLoadingReadiness(true)
    api.readiness().then(value => { if (active) setReadiness(value) }).catch(error => { if (active) onError(errorMessage(error)) }).finally(() => { if (active) setLoadingReadiness(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    setLoadingCatalog(true)
    setLoadError('')
    setModels([])
    setLiveRoutes([])
    setAssessmentRoutes([])
    api.models(provider).then(value => { if (active) setModels(value.models) }).catch(error => { if (active) setLoadError(errorMessage(error)) }).finally(() => { if (active) setLoadingCatalog(false) })
    return () => { active = false }
  }, [provider])

  useEffect(() => {
    if (provider !== 'openrouter') return
    let active = true
    setLoadingRoutes(true)
    const load = async (modelId: string) => {
      if (!modelId) return []
      const response = await api.routes(modelId)
      const choices = new Map<string, RouteChoice>()
      for (const route of response.data.endpoints || []) {
        const id = routeId(route)
        if (id && !choices.has(id)) choices.set(id, { id, name: route.provider_name || route.tag || route.provider_tag || id, pricing: route.pricing, supported_parameters: route.supported_parameters || [] })
      }
      return [...choices.values()]
    }
    Promise.all([load(config.live_model), load(config.assessment_model)]).then(([live, assessment]) => {
      if (active) { setLiveRoutes(live); setAssessmentRoutes(assessment) }
    }).catch(error => {
      if (active) { setLiveRoutes([]); setAssessmentRoutes([]); setLoadError(errorMessage(error)) }
    }).finally(() => { if (active) setLoadingRoutes(false) })
    return () => { active = false }
  }, [provider, config.live_model, config.assessment_model])

  const update = (patch: Partial<ProviderConfig>) => setDraft(current => ({ ...current, providers: { ...current.providers, [current.provider]: { ...current.providers[current.provider], ...patch } } }))
  const selectProvider = (value: Provider) => setDraft(current => ({ ...current, provider: value }))

  const save = async () => {
    setSaving(true)
    try { await onSave(draft); onMessage('Provider and model settings saved.') }
    catch (error) { onError(errorMessage(error)) }
    finally { setSaving(false) }
  }

  const test = async () => {
    if (provider !== 'codex' && !config.paid_opt_in) { onError('Turn on paid processing consent before testing this provider.'); return }
    if (!config.live_model || !config.assessment_model) { onError('Select both an interview model and an assessment model first.'); return }
    if (provider === 'openrouter' && (!config.live_route || !config.assessment_route)) { onError('Choose an approved route for each model first.'); return }
    const confirmation = provider === 'codex'
      ? 'This checks whether the OpenAI connection on the API host is signed in. It does not send synthetic interview prompts. Continue?'
      : `This sends synthetic test prompts to ${providerName} using the current unsaved choices. The provider may charge for these requests.\n\n${pricingDisclosure}\n\nContinue?`
    if (!window.confirm(confirmation)) return
    setTesting(true)
    try {
      const result = await api.testProvider(provider, config)
      onMessage(result.detail || (provider === 'codex' ? 'OpenAI sign-in verified.' : 'Provider passed the synthetic interview and structured-output checks.'))
      const fresh = await api.readiness()
      setReadiness(fresh)
    } catch (error) { onError(errorMessage(error)) }
    finally { setTesting(false) }
  }

  const renderModelOptions = (purpose: 'live' | 'assessment') => models.filter(model => provider === 'codex' ? model.id === 'gpt-6-luna' : purpose === 'live' || model.structured_outputs).map(model => <option key={model.id} value={model.id}>{provider === 'codex' ? 'Luna' : model.name || model.id}</option>)
  const renderRouteOptions = (routes: RouteChoice[]) => routes.map(route => <option key={route.id} value={route.id}>{route.name} · {formatPricing(route.pricing)}</option>)

  return <main className="page-content provider-settings">
    <div className="settings-title"><h1>Settings</h1><p>Provider and model choices apply to interviews you start from now on.</p></div>
    <section className="panel settings-panel" aria-labelledby="provider-settings-heading">
      <div className="panel-heading"><div><h2 id="provider-settings-heading">AI provider and models</h2></div><Settings2 size={19}/></div>
      <p className="panel-copy">Choose the service that processes interview text. Active interviews keep their original settings.</p>
      <label className="field-label">Provider<select value={provider} onChange={event => selectProvider(event.target.value as Provider)}><option value="groq">Groq</option><option value="openrouter">OpenRouter</option><option value="codex">OpenAI</option></select></label>
      <div className="provider-status"><span className={`status-indicator ${providerReady?.validated ? 'status-good' : 'status-unknown'}`}/><div><b>{loadingReadiness ? 'Checking provider status…' : providerReady?.validated ? provider === 'codex' ? 'OpenAI sign-in verified' : 'Provider connection validated' : providerReady?.status === 'configured' ? provider === 'codex' ? 'OpenAI connection available on the API host' : 'Server credentials configured' : provider === 'codex' ? 'OpenAI connection unavailable on the API host' : 'Server credentials missing'}</b><small>{provider === 'codex' ? 'Test connection checks whether the local OpenAI connection is signed in. Interview text is sent to OpenAI using the signed-in subscription.' : providerReady?.status === 'missing' ? 'Add the provider key to the server environment.' : 'Credentials stay on the server and are never shown here.'}</small></div><button className="button-outline" type="button" onClick={test} disabled={testing || loadingCatalog || saving || loadingReadiness || providerReady?.status !== 'configured'}>{testing ? <><LoaderCircle size={14}/> Testing…</> : provider === 'codex' ? 'Check sign-in' : 'Test connection'}</button></div>
      {loadError && <div className="inline-error" role="alert"><TriangleAlert size={15}/>{loadError}<button className="button-quiet" type="button" onClick={() => { setLoadError(''); setLoadingCatalog(true); api.models(provider).then(value => setModels(value.models)).catch(error => setLoadError(errorMessage(error))).finally(() => setLoadingCatalog(false)) }}><RefreshCw size={14}/> Retry</button></div>}
      {loadingCatalog ? <p className="panel-copy" role="status"><LoaderCircle size={15}/> Loading available models…</p> : <div className="model-fields">
        <label className="field-label">Interview model<select value={config.live_model} onChange={event => update({ live_model: event.target.value, ...(provider === 'openrouter' ? { live_route: '' } : {}) })}><option value="">Choose a model</option>{renderModelOptions('live')}</select><small>{formatPricing(liveModel?.pricing)}</small></label>
        <label className="field-label">Review model<select value={config.assessment_model} onChange={event => update({ assessment_model: event.target.value, ...(provider === 'openrouter' ? { assessment_route: '' } : {}) })}><option value="">Choose a model with structured outputs</option>{renderModelOptions('assessment')}</select><small>At interview completion, this model generates a provisional answer rating and coaching. It also groups conversation points.</small><small>{formatPricing(assessmentModel?.pricing)}</small></label>
        {provider === 'openrouter' && <>
          <label className="field-label">Interview provider route<select value={config.live_route} onChange={event => update({ live_route: event.target.value })} disabled={!config.live_model || loadingRoutes}><option value="">{loadingRoutes ? 'Loading model routes…' : 'Choose an approved route'}</option>{renderRouteOptions(liveRoutes)}</select><small>{config.live_model ? `Model: ${config.live_model}. ${liveRoutes.length ? 'Routes are returned by OpenRouter.' : 'No routes returned for this model.'}` : 'Choose a model to load its available routes.'}</small></label>
          <label className="field-label">Review provider route<select value={config.assessment_route} onChange={event => update({ assessment_route: event.target.value })} disabled={!config.assessment_model || loadingRoutes}><option value="">{loadingRoutes ? 'Loading model routes…' : 'Choose an approved route'}</option>{renderRouteOptions(assessmentRoutes.filter(route => route.supported_parameters.includes('structured_outputs')))}</select><small>Only routes that support structured outputs are listed.</small></label>
        </>}
        {provider === 'codex' ? <div className="disclosure provider-cost-note"><CircleHelp size={17}/><p><b>Subscription allowance applies.</b> OpenAI uses the signed-in subscription on the API host. Usage consumes that account’s allowance; OpenAI requests do not go through OpenRouter. No per-token catalog price is available here.</p></div> : <><div className="disclosure provider-cost-note"><CircleHelp size={17}/><p><b>Check pricing before you connect.</b> Unknown pricing is not free. Catalog prices are shown where available, but the provider may charge by token and local billing controls still apply.</p></div>
        <label className="check-row paid-opt-in"><input type="checkbox" checked={config.paid_opt_in} onChange={event => update({ paid_opt_in: event.target.checked })}/><span><b>Allow provider requests that may incur charges</b><small>Required for connection tests and interviews. The server still checks the model and route costs.</small></span></label></>}
        <div className="settings-actions"><button className="button-primary" type="button" onClick={save} disabled={!dirty || saving || loadingCatalog}><Save size={15}/>{saving ? 'Saving…' : 'Save settings'}</button><span>{dirty ? 'Unsaved changes' : <><Check size={14}/> Saved</>}</span></div>
      </div>}
      <div className="privacy-note"><ShieldCheck size={18}/><span><b>API keys remain on the server.</b><small>Provider credentials are never displayed or stored in the browser.</small></span></div>
    </section>
  </main>
}
