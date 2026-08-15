import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'


export default async function globalSetup() {
  const root = path.resolve('..')
  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'quizvault-e2e-'))
  const python = path.join(root, '.venv', 'Scripts', 'python.exe')
  const server = spawn(python, [path.join(root, 'scripts', 'e2e_server.py')], {
    cwd: root,
    env: { ...process.env, QUIZVAULT_DATA_DIR: dataDir },
    stdio: 'ignore',
    windowsHide: true,
  })
  server.unref()

  let ready = false
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (server.exitCode !== null) break
    try {
      const response = await fetch('http://127.0.0.1:8765/api/v1/health?token=e2e-token')
      if (response.ok) {
        ready = true
        break
      }
    } catch {
      // The server is still starting.
    }
    await new Promise(resolve => setTimeout(resolve, 250))
  }
  if (!ready) {
    server.kill()
    await rm(dataDir, { recursive: true, force: true })
    throw new Error('QuizVault E2E server did not become ready')
  }

  return async () => {
    server.kill()
    for (let attempt = 0; attempt < 20 && server.exitCode === null; attempt += 1) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    await rm(dataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 })
  }
}
