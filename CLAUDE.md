# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuizVault — interactive quiz application for studying multiple-choice questions across any subject. Available in two versions:

- **Terminal version** (`quiz.py`) — colored feedback, sequential/random modes, persistent wrong-question book
- **GUI version** (`gui/main.py`) — tkinter-based graphical interface with the same features

Zero external dependencies — Python 3.6+ standard library only. Optional `pyyaml` enables YAML storage format; otherwise JSON is used.

## Commands

```bash
# Run terminal version
python quiz.py

# Run GUI version
python gui/main.py

# Run all tests
python -m pytest test/ -v

# Run a single test file
python -m pytest test/test_bank_manager.py -v

# Run a single test class
python -m pytest test/test_quiz.py::TestMain -v

# Run a single test
python -m pytest test/test_quiz.py::TestMain::test_choice_1_sequential_single -v

# Build terminal executable (produces dist/quiz.exe)
pyinstaller quiz.spec

# Build GUI executable (produces dist/quiz_gui.exe)
pyinstaller gui.spec
```

## Git-ignored Files

Per-bank data files are not committed to git:
- `banks/*/wrong_questions.json` — wrong question records per bank
- `banks/*/collections.json` — user-created collections per bank
- `banks/*/quiz_progress.json` — mid-quiz progress snapshots
- `questions.json` — legacy single-file question storage

## Architecture

**Folder-based bank management** — questions live in `banks/<bank_name>/` subdirectories. Each subfolder is an independent question bank. `bank_manager.py` scans `banks/` at startup, loading `.md` and `.json` files from each subfolder. Multiple files in one folder are merged into a single bank. Per-bank data (wrong questions, collections, flagged questions, deleted questions) is stored as JSON files inside each bank folder.

**Flat structure** — all source files in the project root; GUI files in `gui/`; tests in `test/`. The `banks/` folder contains question bank subfolders, each with `.md` source files and runtime JSON data.

### Module dependency graph

```
quiz.py (terminal application)
  +-- bank_manager.py (bank scanning, per-bank CRUD)
  |     +-- parse_markdown.py (Markdown -> question dicts)
  +-- import_questions.py (import, validate, stats, export CLI)
        +-- parse_markdown.py

gui/main.py (GUI application)
  +-- gui/pages/ (page Frame modules: bank_select, operations, quiz, result, wrong_book, collection, flagged, batch_delete)
  +-- gui/widgets/ (reusable widgets: question_card)
  +-- bank_manager.py (shared with terminal version)
  +-- parse_markdown.py (shared with terminal version)
```

**`quiz.py`** (~2000 lines) — monolithic application. Embeds a fallback `QUESTION_BANK` (75 questions) at the top, then contains all UI, quiz logic, persistence, collections, batch delete, flagged question handling, and the two-layer menu system (bank selection → per-bank operations).

**`bank_manager.py`** (~670 lines) — folder-based bank management module. Key functions:
- `scan_banks_folder()` — scans `banks/` and returns a list of bank dicts with `name`, `path`, `questions`
- Per-bank CRUD: `load_bank_wrong_questions()` / `save_bank_wrong_question()` / `remove_bank_wrong_question()`, `load_bank_collections()` / `save_bank_collection()`, flagged and deleted question management

**`import_questions.py`** (~450 lines) — CLI tool with subcommands: `import`, `validate`, `stats`, `flagged`, `unflag`, `export`. Handles validation, MD5-based deduplication, and YAML/JSON auto-detection.

**`parse_markdown.py`** (~100 lines) — parses Markdown into question dicts. Splits on `---`, detects section headers (`## 单选题`/`## 多选题`) for default type, supports `<!-- single -->` / `<!-- multi -->` per-question overrides.

**`gui/main.py`** — tkinter-based GUI version. Uses a page-based architecture with `gui/pages/` containing individual Frame modules for each screen (bank selection, operations menu, quiz, results, wrong question book, collections, flagged questions, batch delete). Reusable widgets live in `gui/widgets/`. Reuses `bank_manager.py` and `parse_markdown.py` from the terminal version. Package with `pyinstaller gui.spec` to produce `dist/quiz_gui.exe`.

### Data flow

1. Questions originate as Markdown files in `banks/<name>/` folders
2. `parse_markdown.py` converts Markdown to question dicts
3. `bank_manager.py` scans all bank folders, merges multiple files per bank, filters deleted questions
4. `quiz.py` (terminal) or `gui/main.py` (GUI) presents a bank-selection menu, then loads questions from the chosen bank
5. Wrong answers → `banks/<name>/wrong_questions.json`, collections → `collections.json`, etc.

### Question dict format

```python
{
    'id': int,           # question number
    'type': 'single'|'multi',
    'question': str,     # question text
    'options': dict,     # {"A": "text", "B": "text", ...}
    'answer': str,       # "A" or "ABC"
    'explanation': str,
    'source': str,       # source filename (set by parse_markdown)
}
```

Full format spec: see `docs/FORMAT.md`.

## Key Implementation Details

**CJK-aware display**: `_display_width()` uses `unicodedata.east_asian_width()` — Chinese characters count as 2 columns. All box-drawing and padding functions use display width, not `len()`. When modifying any terminal output, use `_pad_to_width()` / `_center_to_width()`, never raw string padding.

**Wrong-question deduplication**: Uses `(id, type)` composite keys because single-choice and multi-choice questions share numeric IDs. `save_wrong_question()` checks for existing entries by this key and increments `wrong_count` instead of duplicating.

**Multi-choice answer comparison**: Both user input and stored answers are sorted before comparison (`"".join(sorted(answer.upper()))`) — order doesn't matter.

**Input validation** (`validate_answer()`): Single-choice accepts exactly one letter A-D. Multi-choice accepts 2+ non-duplicate letters A-D. "Q" or "QUIT" exits.

**ANSI colors**: The `Colors` class defines escape sequences. `print_colored()` wraps them. On Windows, `os.system('')` is called at import time to enable ANSI support.

**Exe packaging**: `quiz.py` determines `BASE_DIR` at startup — when frozen by PyInstaller, it uses `sys._MEIPASS`; otherwise uses the script directory. The `banks/` folder is resolved relative to `BASE_DIR`, so the `.exe` finds banks in its own directory. Build specs: `quiz.spec` (terminal), `gui.spec` (GUI).

**Quiz progress saving**: `quiz_progress.json` in each bank folder stores mid-quiz state (current index, correct count, wrong questions, shuffle permutation). Terminal saves on Q/EOF; GUI saves on back button/Escape/window close. Restored via `run_quiz(resume_data=...)` (terminal) or `QuizPage.refresh(resume_data=...)` (GUI). Uses index-based shuffle to preserve random order across save/restore.

## Documentation Requirements

**Always update READMEs when changing or adding features.** This includes:

- `README.md` — main project README for terminal and shared features
- `gui/README.md` — GUI-specific features and file structure
- `CLAUDE.md` — implementation details relevant to developers

Update the relevant README(s) in the same commit as the feature change. Do not leave README updates for later.
