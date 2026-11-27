# Handover: Sigma full-frame collection, batch 2

**Status: transferred, not started.** Nothing in batch 2 has been transcribed, built or committed. This
package exists so the next agent can pick the work up on another machine without the previous session's
context.

Companion file: [`handover-sigma-ff-2.json`](handover-sigma-ff-2.json) carries the same scope in the
batch schema, so it can be diffed against `records/sigma-ff/batch-sigma-ff-1.json`.

## Where batch 1 stands

| | |
|---|---|
| Branch | `sigma-ff/a1`, commit `525eb4f` |
| Worktree | `/workspace/wt/sigma-a1`, clean, nothing untracked |
| Pull request | [JunLin615/os-optics-lens#44](https://github.com/JunLin615/os-optics-lens/pull/44) — **open**, `mergeable: clean`, 130 files, +139166 lines |
| Records | 43, from six publications |
| Validation | 43/43 `project_check ACCEPTED`, `optical_solids VALID`, `paraxial MATCHED` |

| Publication | Accepted |
|---|---|
| US20250208379A1 | 14 |
| US20250208387A1 | 4 |
| US20250258361A1 | 6 |
| US20250321401A1 | 6 |
| US20250334778A1 | 6 |
| US20260118636A1 | 7 |

No CI is configured on the repository, so #44 is waiting on a human review. **Land or close it before
opening a batch that touches the same collection's format assumptions.**

## What is left, and why it is not a transcription queue

`batch-sigma-ff-1.json` records an outcome and a reason for all 101 inputs. 43 were accepted, **58 were
deferred, and every one of the 58 was deferred for a property of the publication — not a defect in the
transcription.**

| Reason code | Inputs | What it means |
|---|---|---|
| `ZOOM_CONFIGURATIONS_NOT_IN_FORMAT` | 46 | The example prints several zoom positions in its [Variable Distance Data]; a record holds one on-axis configuration. |
| `APS_C_IMAGE_FORMAT` | 9 | The printed image height is APS-C (Y = 14.20 mm). |
| `IMAGE_FORMAT_NOT_FULL_FRAME` | 1 | Y = 27.39 mm, a 54.78 mm image circle — larger than 36 × 24. |
| `SOURCE_TABLE_INCONSISTENT` | 1 | The rendered table cannot reproduce the example's own printed first-order values. |
| `NO_MACHINE_READABLE_TABLE` | 1 | The retrieved page has no parseable [Surface Data] table. |

So batch 2 has **nothing to accept until someone decides what to do about zooms.** That decision changes
the record format, which is a maintainer's call, not an intake agent's.

## The three open questions

### Q1 — Does the corpus want zooms, and in what form? (blocks 46 inputs)

Two forms are viable and the repo already contains the harder half of the second:

1. **One record per zoom position.** Shared prescription repeated, position named in the record. Simple,
   consistent with today's format, but duplicates surface tables and lets the copies drift.
2. **One record, native configurations.** `/workspace/tools/zoom_split.py` already splits an imported
   single-compound Project into per-group components and writes configurations that translate the groups
   along the axis — the native representation. Choosing it needs the record format's configuration block,
   the evidence extract's per-column distances and the batch schema's per-record configuration count
   defined together.

If Q1 is answered "form 2", **27 full-frame zoom inputs become transcribable** (13 + 8 + 6 from
US20250172790A1, US20250244566A1, US20260126629A1). If "form 1", the same 27 are transcribable with more
records. If "no", batch 2 largely does not exist.

### Q2 — Should sub-full-frame publications have their own collection? (9 inputs)

US12196935B2 (5 × APS-C) and US20250383527A1 (4 × APS-C, 1 × 54.78 mm circle) are complete, well-formed
tables. They were deferred only because the frame is smaller (or larger) than 36 × 24. The transcription
cost is already paid in the retrieved pages.

### Q3 — Is US20250208387A1 example 3 worth re-reading? (1 input)

The only source-defect entry in the batch, and the only item an agent can act on without waiting for a
decision:

> [Lens Group Data] prints G1 = 166.46 mm. The rendered table reproduces that only with surface 9 at
> −251.1669 mm, while on that reading the system first-order values still come out 529.09 / 34.78 mm
> against the printed 485.01 / 29.8213 mm. No single or double sign correction reconciles them.

The application's own PDF may settle it. **Do not repair it by fitting signs until the numbers close** —
a `DIFFERS` paraxial verdict is a defect, never something to explain away.

## Picking the work up on another machine

The sandbox does not travel. What travels is the branch and this package.

1. Clone the fork `Hassan-Sau/os-optics-lens`, check out `sigma-ff/a1`, and confirm #44 is still open.
2. Re-create the tooling from `/workspace/tools/` — `PLAYBOOK.md` is the pipeline, `build_record.py` is the
   builder, `zoom_split.py` is the zoom path. They are plain Python against
   `/root/venv/bin/os-optics` (0.14.0, catalog 2026-11-25.1).
3. Re-fetch the pages you need with `fetch_pages.py` / `fetch_pages2.py`. The retained HTML in
   `/workspace/build/pages/` is the only machine-readable source — the PDFs are image-only — and it does
   not survive this sandbox.
4. Get Q1 and Q2 answered before transcribing anything.

Known fetch failures, so nobody re-burns time on them blind: `US4624536A` and `US4647171A` returned 404
after four retries; `US20250370233A1` and `US20260227611A1` returned empty bodies; `US12724248B2`
retrieved but renders no table.

## Working rules that are easy to get wrong

- Read `record.json → validation` after every build. Exit code 0 only means the Project imported.
- `paraxial` tolerance is `atol 0.005 mm + rtol 3e-4 × scale`. `DIFFERS` means a transcription defect or a
  source defect — find the row, do not loosen the test.
- Every quantity carries a `basis`: `SOURCE_STATED`, `DERIVED` or `ENGINE_COMPUTED`. Absent values are
  `null`, never a guess.
- One record per numerical example; one `design_family_id` per publication.
- Commit the native Project, the record and the evidence extract. Not `lens.csv`, `import.json` or
  `report.json`.
- English for everything committed.
