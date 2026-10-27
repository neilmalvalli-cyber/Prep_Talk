/// <reference types="vite/client" />

import { useEffect, useState } from 'react'
import {useTheme} from './Theme'

import Editor, { loader, type EditorProps } from '@monaco-editor/react'

import * as monaco from 'monaco-editor/editor'

import 'monaco-editor/features/register.all'

import 'monaco-editor/languages/definitions/python/register'

import 'monaco-editor/languages/definitions/cpp/register'

import editorWorker from 'monaco-editor/editor/editor.worker?worker'



Object.assign(self, {MonacoEnvironment: {getWorker() {return new editorWorker()}}})

loader.config({ monaco })



export default function LocalEditor(props: EditorProps) {

  const {theme}=useTheme()

  const [failed, setFailed] = useState(false)

  const [ready, setReady] = useState(false)

  useEffect(() => {

    if (ready || failed) return

    const timer = window.setTimeout(() => setFailed(true), 15_000)

    return () => window.clearTimeout(timer)

  }, [ready, failed])

  if (failed) return <textarea className="editor-fallback" aria-label="Code editor" value={typeof props.value === 'string' ? props.value : ''} onChange={event => props.onChange?.(event.target.value, {} as monaco.editor.IModelContentChangedEvent)} spellCheck={false} style={{ width: '100%', height: props.height || 330, resize: 'vertical', background: 'var(--field)', color: 'var(--text)', fontFamily: 'ui-monospace, Consolas, monospace', padding: 16 }}/>

  return <Editor theme={theme==='dark'?'vs-dark':'light'} {...props} onMount={(editor, instance) => { setReady(true); props.onMount?.(editor, instance) }} onValidate={markers => props.onValidate?.(markers)} loading={<div className="editor-loading" role="status">Loading the local code editor…</div>} options={{ ...props.options, accessibilitySupport: 'on', ariaLabel: 'Code editor', tabFocusMode: true }}/>

}

