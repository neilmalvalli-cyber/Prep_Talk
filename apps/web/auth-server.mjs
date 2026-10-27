import { createServer } from 'node:http'
import { randomBytes } from 'node:crypto'
import { mkdirSync, readFileSync, writeFileSync, chmodSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import Database from 'better-sqlite3'
import { betterAuth } from 'better-auth'
import { getMigrations } from 'better-auth/db/migration'
import { toNodeHandler } from 'better-auth/node'
import { jwt, username } from 'better-auth/plugins'

const envPath = resolve(process.cwd(), '../../.env')
try { process.loadEnvFile(envPath) } catch {}
const origin = process.env.FIELDNOTE_ORIGIN || 'http://localhost:5173'
const dataDir = resolve(process.cwd(), '../../data')
mkdirSync(dataDir, { recursive: true })
const secretPath = resolve(dataDir, 'auth.secret')
if (!process.env.BETTER_AUTH_SECRET && !existsSync(secretPath)) {
  writeFileSync(secretPath, randomBytes(32).toString('base64url'), { mode: 0o600 })
  try { chmodSync(secretPath, 0o600) } catch {}
}
const secret = process.env.BETTER_AUTH_SECRET || readFileSync(secretPath, 'utf8').trim()
const database = new Database(resolve(dataDir, 'auth.sqlite3'))
database.pragma('journal_mode = WAL')

const authOptions = {
  database,
  baseURL: origin,
  basePath: '/api/auth',
  secret,
  trustedOrigins: [origin],
  emailAndPassword: { enabled: true },
  plugins: [username(), jwt({ jwt: { expirationTime: '5m' } })],
}
const { runMigrations } = await getMigrations(authOptions)
await runMigrations()
const auth = betterAuth(authOptions)

const server = createServer(toNodeHandler(auth))
const port = Number(process.env.FIELDNOTE_AUTH_PORT || 8001)
const host = process.env.FIELDNOTE_AUTH_HOST || '127.0.0.1'
server.listen(port, host, () => {
  console.log(`Fieldnote auth listening on ${host}:${port}; origin ${origin}`)
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.close(() => database.close()))
}
