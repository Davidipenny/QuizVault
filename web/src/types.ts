export type QuestionType = 'single' | 'multi' | 'any' | 'truefalse' | 'fill' | 'essay'

export interface Bank {
  id: string; name: string; description: string; tags: string[]; challenge_size: number
  archived: boolean; version: number; question_count: number; last_studied_at?: string
}

export interface Choice { id?: string; label: string; content: string; is_correct?: boolean; display_order?: number }
export interface Question {
  id?: string; bank_id?: string; type: QuestionType; prompt: string; case_material: string
  explanation: string; source: string; sort_order?: number; choices: Choice[]; answer_spec?: Record<string, any>
  answer_meta?: { blank_count?: number; unordered?: boolean }
}

export interface StudyState {
  id: string; question_id: string; wrong_count: number; favorite: boolean; note: string
  flagged: boolean; mastery: string; last_answered_at?: string; question: Question
}
