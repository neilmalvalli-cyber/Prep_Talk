import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

const authHost = process.env.FIELDNOTE_AUTH_HOST || '127.0.0.1'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: [{
    // Monaco ships a vendored sanitizer, so an npm override alone does not
    // replace the vulnerable copy that its editor imports into the bundle.
    find: /^\.\/dompurify\/dompurify\.js$/,
    replacement: fileURLToPath(new URL('./node_modules/dompurify/dist/purify.es.mjs', import.meta.url)),
  }] },
  server: { proxy: { '/api/auth': `http://${authHost}:8001`, '/api': 'http://127.0.0.1:8000' } },
})
