from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
QuestionType = Literal["single", "multi", "any", "truefalse", "fill", "essay"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BankCreate(StrictModel):
    name: NonEmpty
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    challenge_size: int = Field(20, ge=0, le=3000)


class BankUpdate(StrictModel):
    name: NonEmpty = None
    description: str = None
    tags: list[str] = None
    challenge_size: int = Field(None, ge=0, le=3000)
    archived: bool = None


class BankMerge(StrictModel):
    source_bank_id: NonEmpty


class ChoiceInput(StrictModel):
    label: NonEmpty
    content: str
    is_correct: bool = False
    display_order: int = Field(0, ge=0)


class SelectionAnswerSpec(StrictModel):
    correct: list[NonEmpty]


class TrueFalseAnswerSpec(StrictModel):
    value: bool


class FillAnswerSpec(StrictModel):
    blanks: list[list[NonEmpty]] = Field(min_length=1)
    unordered: bool = False

    @field_validator("blanks")
    @classmethod
    def validate_blanks(cls, value):
        if any(not blank for blank in value):
            raise ValueError("每个空至少需要一个可接受答案")
        return value


class EssayAnswerSpec(StrictModel):
    reference: NonEmpty


class QuestionFields(StrictModel):
    prompt: NonEmpty
    case_material: str = ""
    explanation: str = ""
    source: str = ""
    sort_order: int = Field(0, ge=0)
    choices: list[ChoiceInput] = Field(default_factory=list)


class SingleQuestion(QuestionFields):
    type: Literal["single"]
    answer_spec: SelectionAnswerSpec


class MultiQuestion(QuestionFields):
    type: Literal["multi"]
    answer_spec: SelectionAnswerSpec


class AnyQuestion(QuestionFields):
    type: Literal["any"]
    answer_spec: SelectionAnswerSpec


class TrueFalseQuestion(QuestionFields):
    type: Literal["truefalse"]
    answer_spec: TrueFalseAnswerSpec


class FillQuestion(QuestionFields):
    type: Literal["fill"]
    answer_spec: FillAnswerSpec


class EssayQuestion(QuestionFields):
    type: Literal["essay"]
    answer_spec: EssayAnswerSpec


QuestionRequest = Annotated[
    Union[SingleQuestion, MultiQuestion, AnyQuestion, TrueFalseQuestion, FillQuestion, EssayQuestion],
    Field(discriminator="type"),
]


class BatchQuestions(StrictModel):
    question_ids: list[NonEmpty] = Field(min_length=1)
    action: Literal["delete", "move", "copy"]
    target_bank_id: str | None = None


class ImportPreview(StrictModel):
    bank_id: NonEmpty
    source_type: Literal["text", "json", "ai_json", "excel", "word"] = "text"
    content: str
    filename: str = ""


class ImportEdit(StrictModel):
    rows: list[dict[str, Any]]


class LegacyCommit(StrictModel):
    path: str = ""


class QuizConfig(StrictModel):
    scope: Literal["all", "wrong", "favorite", "unanswered"] = "all"
    types: list[QuestionType] = Field(default_factory=list)
    order: Literal["sequential", "random"] = "sequential"
    shuffle_options: bool = False
    study_mode: bool = False
    auto_next: bool = False
    compare_essay: bool = False
    limit: int = Field(0, ge=0, le=3000)


class QuizSessionCreate(StrictModel):
    bank_id: NonEmpty
    config: QuizConfig = Field(default_factory=QuizConfig)


class AnswerSubmit(StrictModel):
    question_id: NonEmpty
    answer: dict[str, Any]


class QuizSessionUpdate(StrictModel):
    current_index: int = Field(None, ge=0)
    status: Literal["active", "abandoned", "completed"] = None


class StudyStateUpdate(StrictModel):
    favorite: bool = None
    note: str = None
    flagged: bool = None
    mastery: Literal["new", "learning", "mastered"] = None
    wrong_count: int = Field(None, ge=0)


class CollectionCreate(StrictModel):
    name: NonEmpty


class CollectionUpdate(CollectionCreate):
    pass


class CollectionQuestionAdd(StrictModel):
    question_id: NonEmpty


class RestoreRequest(StrictModel):
    content: NonEmpty
