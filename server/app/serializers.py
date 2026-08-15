from __future__ import annotations

from .models import Choice, Question, QuestionBank, QuizAnswer, QuizSession, StudyState


def choice_dict(choice: Choice, include_answer: bool = True) -> dict:
    data = {
        "id": choice.id,
        "label": choice.label,
        "content": choice.content,
        "display_order": choice.display_order,
    }
    if include_answer:
        data["is_correct"] = choice.is_correct
    return data


def question_dict(question: Question, include_answer: bool = True) -> dict:
    data = {
        "id": question.id,
        "bank_id": question.bank_id,
        "type": question.type,
        "prompt": question.prompt,
        "case_material": question.case_material,
        "explanation": question.explanation if include_answer else "",
        "source": question.source,
        "sort_order": question.sort_order,
        "version": question.version,
        "choices": [choice_dict(c, include_answer) for c in question.choices],
    }
    if include_answer:
        data["answer_spec"] = question.answer_spec
    else:
        data["answer_meta"] = answer_meta(question)
    return data


def answer_meta(question: Question) -> dict:
    if question.type == "fill":
        blanks = (question.answer_spec or {}).get("blanks") or []
        return {"blank_count": len(blanks), "unordered": bool((question.answer_spec or {}).get("unordered"))}
    return {}


def bank_dict(bank: QuestionBank, question_count: int = 0, last_studied_at=None) -> dict:
    return {
        "id": bank.id,
        "name": bank.name,
        "description": bank.description,
        "tags": bank.tags or [],
        "challenge_size": bank.challenge_size,
        "version": bank.version,
        "archived": bank.archived,
        "question_count": question_count,
        "last_studied_at": last_studied_at,
        "created_at": bank.created_at,
        "updated_at": bank.updated_at,
    }


def state_dict(state: StudyState, question: Question | None = None) -> dict:
    data = {
        "id": state.id,
        "question_id": state.question_id,
        "wrong_count": state.wrong_count,
        "favorite": state.favorite,
        "note": state.note,
        "flagged": state.flagged,
        "last_answered_at": state.last_answered_at,
        "mastery": state.mastery,
    }
    if question:
        data["question"] = question_dict(question)
    return data


def answer_dict(answer: QuizAnswer) -> dict:
    return {
        "id": answer.id,
        "question_id": answer.question_id,
        "answer": answer.answer,
        "question_snapshot": answer.question_snapshot,
        "is_correct": answer.is_correct,
        "answered_at": answer.answered_at,
    }


def session_dict(session: QuizSession, answers: list[QuizAnswer] | None = None) -> dict:
    return {
        "id": session.id,
        "bank_id": session.bank_id,
        "config": session.config,
        "question_order": session.question_order,
        "current_index": session.current_index,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "completed_at": session.completed_at,
        "answers": [answer_dict(a) for a in answers or []],
    }
