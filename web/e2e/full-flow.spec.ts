import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { expect, test } from 'playwright/test'


const headers = { 'X-QuizVault-Token': 'e2e-token' }
const questions = [
  { type: 'single', prompt: '单选', choices: [{ label: 'A', content: '甲' }, { label: 'B', content: '乙' }], answer_spec: { correct: ['A'] } },
  { type: 'multi', prompt: '多选', choices: [{ label: 'A', content: '甲' }, { label: 'B', content: '乙' }], answer_spec: { correct: ['A', 'B'] } },
  { type: 'any', prompt: '任意选', choices: [{ label: 'A', content: '甲' }, { label: 'B', content: '乙' }], answer_spec: { correct: ['A'] } },
  { type: 'truefalse', prompt: '判断', answer_spec: { value: true } },
  { type: 'fill', prompt: '两空填空', answer_spec: { blanks: [['甲'], ['乙']], unordered: false } },
  { type: 'essay', prompt: '问答', answer_spec: { reference: '参考答案' } },
]

async function createSixTypeBank(request: any) {
  const bank = await (await request.post('/api/v1/banks', { headers, data: { name: `E2E 六类题库 ${Date.now()}` } })).json()
  const preview = await (await request.post('/api/v1/imports/preview', {
    headers,
    data: { bank_id: bank.id, source_type: 'ai_json', content: JSON.stringify(questions) },
  })).json()
  const committed = await request.post(`/api/v1/imports/${preview.id}/commit`, { headers })
  expect((await committed.json()).committed).toBe(6)
  return bank
}

test('API workflow covers migration, six question types, resume, study state, and backup restore', async ({ request }) => {
  const bank = await createSixTypeBank(request)
  const listing = await (await request.get(`/api/v1/banks/${bank.id}/questions`, { headers })).json()
  const byType = Object.fromEntries(listing.items.map((item: any) => [item.type, item]))

  const normal = await (await request.post('/api/v1/quiz-sessions', { headers, data: { bank_id: bank.id, config: {} } })).json()
  const normalLoaded = await (await request.get(`/api/v1/quiz-sessions/${normal.id}`, { headers })).json()
  for (const question of normalLoaded.questions) {
    expect(question.answer_spec).toBeUndefined()
    expect(question.explanation).toBe('')
    expect(question.choices.every((choice: any) => choice.is_correct === undefined)).toBe(true)
  }
  expect(normalLoaded.questions.find((item: any) => item.type === 'fill').answer_meta).toEqual({ blank_count: 2, unordered: false })

  await request.patch(`/api/v1/quiz-sessions/${normal.id}`, { headers, data: { current_index: 3 } })
  const active = await (await request.get('/api/v1/quiz-sessions/active', { headers })).json()
  expect(active.find((item: any) => item.id === normal.id).current_index).toBe(3)
  expect((await (await request.get(`/api/v1/quiz-sessions/${normal.id}`, { headers })).json()).current_index).toBe(3)

  const wrongSession = await (await request.post('/api/v1/quiz-sessions', { headers, data: { bank_id: bank.id, config: { types: ['single'] } } })).json()
  await request.post(`/api/v1/quiz-sessions/${wrongSession.id}/answers`, { headers, data: { question_id: byType.single.id, answer: { selected: ['B'] } } })
  await request.patch(`/api/v1/study-states/${byType.single.id}`, { headers, data: { favorite: true, note: 'E2E 笔记', flagged: true } })
  const collection = await (await request.post('/api/v1/collections', { headers, data: { name: 'E2E 收藏夹' } })).json()
  await request.post(`/api/v1/collections/${collection.id}/questions`, { headers, data: { question_id: byType.single.id } })
  expect((await (await request.get(`/api/v1/study-states?kind=wrong&bank_id=${bank.id}`, { headers })).json()).total).toBe(1)
  expect((await (await request.get(`/api/v1/study-states?kind=unanswered&bank_id=${bank.id}`, { headers })).json()).total).toBe(5)

  const answers: Record<string, any> = {
    single: { selected: ['A'] }, multi: { selected: ['A', 'B'] }, any: { selected: ['A'] },
    truefalse: { value: true }, fill: { values: ['甲', '乙'] }, essay: { text: '参考答案' },
  }
  for (const type of Object.keys(answers)) {
    const session = await (await request.post('/api/v1/quiz-sessions', { headers, data: { bank_id: bank.id, config: { types: [type], compare_essay: true } } })).json()
    const result = await (await request.post(`/api/v1/quiz-sessions/${session.id}/answers`, {
      headers, data: { question_id: byType[type].id, answer: answers[type] },
    })).json()
    expect(result.is_correct).toBe(true)
  }
  expect((await (await request.get(`/api/v1/study-states?kind=unanswered&bank_id=${bank.id}`, { headers })).json()).total).toBe(0)

  const legacyPath = path.resolve('../server/tests/fixtures/legacy_complete')
  const legacyPreview = await request.get(`/api/v1/migration/legacy/preview?path=${encodeURIComponent(legacyPath)}`, { headers })
  expect((await legacyPreview.json()).summary.migratable).toBeGreaterThan(0)
  const migrated = await request.post('/api/v1/migration/legacy/commit', { headers, data: { path: legacyPath } })
  expect((await migrated.json()).questions).toBeGreaterThanOrEqual(2)

  const backup = await (await request.post('/api/v1/backups', { headers })).json()
  const download = await request.get(`/api/v1/backups/${backup.filename}`, { headers })
  const bytes = await download.body()
  expect(bytes.subarray(0, 16).toString()).toBe('SQLite format 3\u0000')
  const restored = await request.post('/api/v1/backups/restore', { headers, data: { content: bytes.toString('base64') } })
  expect((await restored.json()).restored).toBe(true)

  const fixture = await readFile(path.resolve('../server/tests/fixtures/legacy_complete/示例旧题库/questions.json'), 'utf8')
  expect(fixture).toContain('JSON 题目')
})

test.describe('Chromium UI', () => {
  test.skip(Boolean(process.env.QV_E2E_API_ONLY), 'API-only fallback does not require browser assets')

  test('renders multi-blank inputs and reveals study answers on demand', async ({ page, request }) => {
    const bank = await createSixTypeBank(request)
    const fillSession = await (await request.post('/api/v1/quiz-sessions', { headers, data: { bank_id: bank.id, config: { types: ['fill'] } } })).json()
    await page.goto(`/?token=e2e-token#/quiz/${fillSession.id}`)
    await expect(page.locator('.fill-list .el-input')).toHaveCount(2)
    await expect(page.getByText('参考答案')).toHaveCount(0)

    const studySession = await (await request.post('/api/v1/quiz-sessions', { headers, data: { bank_id: bank.id, config: { types: ['truefalse'], study_mode: true } } })).json()
    await page.goto(`/?token=e2e-token#/quiz/${studySession.id}`)
    await expect(page.getByText('参考答案')).toHaveCount(0)
    await page.getByRole('button', { name: '查看答案' }).click()
    await expect(page.getByText('参考答案').first()).toBeVisible()
  })
})
