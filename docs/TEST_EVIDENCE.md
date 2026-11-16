# Test evidence

Commands were executed on Windows 11 (Python 3.12.15 venv, Node 24.14.1) unless stated otherwise. Results are copied from the actual runs; nothing here is a projected result.

## Upstream repositories (Phase 0, 2026-11-15)
| Command | Result |
|---|---|
| Repo A `python -m pytest -q -p no:cacheprovider` | 122 passed, exit 0 |
| Repo B `python -m pytest -q -p no:cacheprovider` | 200 passed, 8 failed, 3 skipped, exit 1 (Windows-specific: file locks, POSIX modes, symlink privilege, `os.killpg`) |

## Backend (Project 3)
| Date | Command | Result |
|---|---|---|
| 2026-11-16 | `python -m pytest -q` | 98 passed (first full run; 1 PDF-export failure fixed beforehand — fpdf2 cursor position) |
| 2026-11-16 | `python -m ruff check backend pipelines` | All checks passed |

## Frontend
| Date | Command | Result |
|---|---|---|
| 2026-11-16 | `npx tsc --noEmit` | exit 0 |
| 2026-11-16 | `npx eslint .` | exit 0 (after fixing one `react-hooks/refs` error in `lib/api.ts`) |
| 2026-11-16 | `npx vitest run` | 2 files, 9 tests passed |
| 2026-11-16 | `npx next build` | compiled; 11 routes prerendered (static shells) |

## Dataset build, end-to-end and visual QA
_Appended below after each run._
