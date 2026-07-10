# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

QuizVault — interactive quiz application for studying questions across any subject. Supports three question types:

- **判断题 (truefalse)** — 2 options (正确/错误), answer A or B
- **单选题 (single)** — 3-4 options, answer one letter A-D
- **多选题 (multi)** — 3-4 options, answer 2-4 letters A-D

GUI version only (`gui/main.py`). Terminal version preserved in `legacy/` but no longer maintained.

Zero external dependencies — Python 3.6+ standard library only. Optional `pyyaml` enables YAML storage format; otherwise JSON is used.

## Commands

```bash
# Run GUI version
python gui/main.py

# Run all tests
python -m pytest test/ -v

# Run a single test file (pytest-style)
python -m pytest test/test_bank_manager.py -v

# Run a single test class (unittest-style tests also run via pytest)
python -m pytest test/test_import_questions.py::TestValidateQuestion -v

# Run a single test
python -m pytest test/test_bank_manager.py::test_scan_banks_folder_returns_list -v

# Run unittest tests directly (parse_markdown, import_questions use unittest)
python -m unittest test.test_parse_markdown -v
python -m unittest test.test_import_questions.TestComputeHash -v

# Build GUI executable (produces dist/quiz_gui.exe)
pyinstaller gui.spec

# CLI import tool
python import_questions.py import 题目.md
python import_questions.py validate 题目.md
python import_questions.py stats
```

Note: `test_bank_manager.py` uses pytest-style functions; `test_parse_markdown.py` and `test_import_questions.py` use `unittest.TestCase` classes. Both run under `pytest`.

## Git-ignored Files

Per-bank data files are not committed to git:
- `banks/*/wrong_questions.json` — wrong question records per bank
- `banks/*/collections.json` — user-created collections per bank
- `banks/*/quiz_progress.json` — mid-quiz progress snapshots
- `banks/*/flagged.json` — flagged questions per bank
- `banks/*/deleted.json` — deleted question records per bank
- `questions.json` — legacy single-file question storage

## Architecture

**Folder-based bank management** — questions live in `banks/<bank_name>/` subdirectories. Each subfolder is an independent question bank. `bank_manager.py` scans `banks/` at startup, loading `.md` and `.json` files from each subfolder. Multiple files in one folder are merged into a single bank. Per-bank data (wrong questions, collections, flagged questions, deleted questions) is stored as JSON files inside each bank folder. Deleted questions use a `deleted.json` allowlist — source files remain untouched.

**Flat structure** — all source files in the project root; GUI files in `gui/`; tests in `test/`. The `banks/` folder contains question bank subfolders, each with `.md` source files and runtime JSON data.

### Module dependency graph

```
gui/main.py (GUI application — only active version)
  +-- gui/pages/ (page Frame modules: bank_select, operations, quiz, result, wrong_book, collection, flagged, batch_delete)
  +-- gui/widgets/ (reusable widgets: question_card)
  +-- bank_manager.py (bank scanning, per-bank CRUD — ~750 lines)
  |     +-- parse_markdown.py (Markdown -> question dicts)
  +-- import_questions.py (import, validate, stats, export CLI — ~460 lines)
        +-- parse_markdown.py
```

### Page routing

`main.py`'s `App` class manages page switching via `show_page(page_name)`:

```
bank_select → operations → quiz → result
                          → wrong_book
                          → collection → collection_detail
                          → flagged
                          → batch_delete
```

Each page is a `tk.Frame` subclass stored in `App.pages` dict. Switching hides the current page and shows the new one.

### Data flow

1. Questions originate as Markdown files in `banks/<name>/` folders
2. `parse_markdown.py` converts Markdown to question dicts
3. `bank_manager.py` scans all bank folders, merges multiple files per bank, filters deleted questions (from `deleted.json`)
4. `gui/main.py` presents a bank-selection menu, then loads questions from the chosen bank
5. Wrong answers → `banks/<name>/wrong_questions.json`, collections → `collections.json`, etc.

### Question dict format

```python
{
    'id': int,           # question number
    'type': 'truefalse'|'single'|'multi',
    'question': str,     # question text
    'options': dict,     # {"A": "text", "B": "text", ...} — 2 for truefalse, 3-4 for single/multi
    'answer': str,       # "A" or "B" (truefalse), "A"-"D" (single), "AB"-"ABCD" (multi)
    'explanation': str,
    'source': str,       # source filename (set by parse_markdown or bank_manager)
}
```

Full format spec: see `docs/FORMAT.md`.

## Key Implementation Details

**`(id, type)` composite key pattern**: Single-choice and multi-choice questions share numeric ID ranges (e.g. both have ID 1), so all per-question lookups use `(id, type)` as a composite key. This pattern is used universally: wrong questions (`wrong_questions.json`), collections (`collections.json`), flagged (`flagged.json`), deleted (`deleted.json`), and quiz progress restore. Always use this composite key when referencing questions in runtime data.

**Widget architecture**: `QuestionCard` (`gui/widgets/question_card.py`) is the reusable question display component used by both `QuizPage` and other pages. It handles three render modes: Radiobuttons for single/truefalse, Checkbuttons for multi. Supports keyboard selection (A/B/C/D), locking after submission, and feedback display.

**Collection unified format (v1.4+)**: All collections now use the dict format `{"created": "...", "questions": [{"id": 1, "type": "single", "added_at": "..."}]}`. `save_bank_collection()` was rewritten to create dict format instead of plain list. Old list-format collections are auto-migrated to dict format on first modification by `save_bank_collection()`, `add_to_bank_collection()`, or `remove_from_bank_collection()`. The helper `_get_collection_questions()` in `collection.py` retains backward compatibility with both formats for display. Use `get_collection_names(bank_path)` to get sorted collection names. New collection entries from quiz page use `create_bank_collection()` + `add_to_bank_collection()` for consistency. The `CollectionPickerDialog` (`quiz.py`) shows existing collections in a selectable list with text entry for new names, replacing the old `simpledialog.askstring`-only approach.

**Two separate data storage systems**: The CLI tool (`import_questions.py`) and the GUI app have independent storage:
- **CLI import tool**: stores all questions in a single `questions.yaml` (or `questions.json` fallback) with `meta` metadata. Uses `content_hash` (MD5 first 8 chars) for dedup across imports. Options converted to list format for YAML storage.
- **GUI app**: reads questions from per-bank `.md`/`.json` files, stores runtime data (wrong questions, collections, etc.) per-bank as separate JSON files. No content hash dedup — relies on `deleted.json` allowlist instead.
Both share `parse_markdown.py` as the common Markdown parser.

**Flagged page edits source Markdown**: The `flagged.py` page allows editing flagged questions directly. It locates the question in the source `.md` file using regex (`\*\*(\d+)\.\s*(.+?)（\s*）.*?\*\*`), splits the file on `---` delimiters, rewrites the relevant block, and joins back. This is the only GUI page that modifies source `.md` files — all other mutations go through JSON runtime files. The regex-based approach is brittle: it depends on consistent `---` delimiters and marker comments (`<!-- single -->`, `<!-- multi -->`) for type overrides.

**Wrong-question deduplication**: Uses `(id, type)` composite keys. `save_wrong_question()` checks for existing entries by this key and increments `wrong_count` instead of duplicating. `remove_bank_wrong_question()` removes from ALL wrong books simultaneously when a question is answered correctly. The wrong book list (`wrong_book.py`) displays both unique question count and cumulative error count (e.g., `"name（5 题, 累计错误 12 次）"`).

**Multi-choice answer comparison**: Both user input and stored answers are sorted before comparison (`"".join(sorted(answer.upper()))`) — order doesn't matter.

**Input validation**: True/false accepts A or B only. Single-choice accepts exactly one letter in available range. Multi-choice accepts 2+ non-duplicate letters. Validation is dynamic based on option count (2-4 options, not always 4).

**Quiz progress save/restore**: `QuizPage._save_progress()` stores current index, correct count, wrong questions (by id+type), `question_order` (index-based shuffle permutation), and `answers` (list of per-question answer snapshots for review mode). `refresh(resume_data=...)` restores by indexing into the shuffled original list. Called on back button, Escape, and window close. Progress file auto-deletes when quiz completes (`_show_result()` calls `delete_quiz_progress()`). This prevents the operations page from prompting "是否继续?" after a completed quiz.

**Answer history review**: `QuizPage` stores per-question answer snapshots in `self.answers` dict (keyed by question index, containing `user_answer`, `is_correct`, `correct_answer`, `explanation`). After submitting a question, users can press `← 上一题` to navigate back to any previously answered question in read-only review mode (locked options + feedback display). `_show_question()` branches between review mode (`current_idx in self.answers`) and active mode (normal answering). `_next()` advances within the answered range; `_prev()` goes back. `_show_review_question()` restores the user's selection, locks options, and shows correctness feedback with explanation.

**Exe packaging**: `gui/main.py` determines `BASE_DIR` — when frozen by PyInstaller, uses `sys._MEIPASS`; otherwise uses the project root. The `banks/` folder resolves relative to `BASE_DIR`. Build spec: `gui.spec`. Windows High DPI awareness is set at module level via `windll.shcore.SetProcessDpiAwareness(1)` before any tk window is created.

**Font scaling (v1.4+)**: `App` class (`main.py`) has `font_scale` (0.6-2.0), `get_font(base_size, bold=False)`, `increase_font()`, and `decrease_font()`. All pages call `self.app.get_font(N)` instead of hardcoded `("Microsoft YaHei", N)`. The `QuestionCard` accepts an `app` reference and uses `_font()` helper that delegates to `self.app.get_font()` when available. Font +/- buttons are on the operations page; changing font triggers `refresh()` on the visible page. When adding new UI code, always use `self.app.get_font(N)`.

**Scrollable quiz layout (v1.4+)**: `QuizPage._build_ui()` wraps the QuestionCard in a Canvas + Scrollbar within a `scroll_container`. The submit button and bottom action bar are children of the QuizPage frame packed AFTER the scroll container, so they remain visible regardless of content length. Mouse wheel scroll is bound on canvas enter/leave. When modifying quiz layout, keep submit_btn and action buttons outside the scroll container to prevent them from scrolling out of view.

**Bank scanning reads `.md` and `.json`**: `_load_bank_questions()` in `bank_manager.py` loads `.md` files (via `parse_markdown`) and `.json` files (direct dict-with-questions or list formats). It filters out questions listed in `deleted.json` using `(id, type)` composite keys. JSON questions keep their existing `source` field; Markdown questions get the filename as `source`.

**No package structure**: The project has no `setup.py`/`pyproject.toml`. Every module (pages, test files) uses `sys.path.insert(0, ...)` to add the project root to the import path at runtime. There is no installed package — imports depend on the working directory or these path hacks.

**Test patterns**: Tests use both pytest functions and `unittest.TestCase`. `test_bank_manager.py` uses pytest functions with `tempfile.TemporaryDirectory` for filesystem isolation — every test creates its own temp directory. `test_parse_markdown.py` and `test_import_questions.py` use `unittest.TestCase`. Both styles run under `pytest`. Test data is never committed — banks data is generated inline in each test.

## Documentation Requirements

**Always update READMEs when changing or adding features.** This includes:

- `README.md` — main project README
- `gui/README.md` — GUI-specific features and file structure
- `AGENTS.md` — implementation details relevant to developers
- `docs/FORMAT.md` — question format specification

Update the relevant README(s) in the same commit as the feature change. Do not leave README updates for later.

## Versioning & Release Workflow

**Every bug fix and feature update must bump the version number.** The version is tracked in the README and the release zip filename (`QuizVault-GUI-v<version>.zip`). When a zip is updated, also update the `.gitignore` to keep the old zip ignored.

**Before committing and pushing to GitHub, always clear locally auto-generated test data** — these are runtime files that get regenerated when the program runs, not source data:

```bash
# Clear all per-bank runtime data (wrong questions, collections, progress, flags, deleted records)
find banks/ -name 'wrong_questions.json' -delete
find banks/ -name 'collections.json' -delete
find banks/ -name 'quiz_progress.json' -delete
find banks/ -name 'flagged.json' -delete
find banks/ -name 'deleted.json' -delete
```

These files are already git-ignored, but clearing them ensures no stale test data leaks into a fresh clone. After clearing, commit the source changes and push to GitHub.
