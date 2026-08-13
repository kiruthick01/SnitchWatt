# Snitchwatt — Project Roadmap

**Snitchwatt** is a from-scratch TVLA (Test Vector Leakage Assessment)
leakage-auditing toolkit — the name is a play on "snitch" (the device gives
up its secrets involuntarily) and "watt" (the unit of electrical power this
tool measures leakage through).

**This document is the single source of truth for this project.** It
contains the full context, architecture, and phased build plan needed to
implement it from scratch with no other prior conversation history. Read it
fully before writing any code.

**Naming note:** project name is finalized as **Snitchwatt**. Use
`snitchwatt` as the folder/package name (Python package: `snitchwatt`,
importable as `import snitchwatt`).

---

## 1. Quick Facts

| | |
|---|---|
| **Project name** | Snitchwatt (folder/package: `snitchwatt`) |
| **One-liner** | A from-scratch implementation of TVLA (Test Vector Leakage Assessment) — the statistical method real hardware security labs use to detect whether a device leaks secret-dependent data through its power consumption — built and validated entirely in software. |
| **Category** | Applied statistics / hardware security / Python tooling |
| **Current scope** | **Software only.** No physical hardware, no oscilloscope, no target device. Validated against simulated power traces using a standard, well-documented leakage model. Hardware capture integration is explicitly deferred (see §7, Phase 5+) until budget allows. |
| **Hardware budget right now** | ₹0 |
| **Estimated build time** | 4–5 days of part-time work across the phases below |
| **Primary toolchain** | Python 3, numpy, scipy (`stats.ttest_ind`), matplotlib, pytest |
| **End goal** | A working, tested, well-documented GitHub repo demonstrating a real industry-standard security-analysis technique, with a clear, honest roadmap for adding real hardware capture later |

---

## 2. Motivation & Background

**What TVLA actually is:** Test Vector Leakage Assessment is a statistical
methodology for answering one specific question about a cryptographic
device: *"does this device's power consumption depend on secret data, in a
way that's statistically distinguishable from noise?"* — without needing to
already know the secret key. This is the same class of technique used by
commercial hardware security certification labs (e.g. Riscure) to certify
smart cards, payment terminals, and secure elements before they ship.

This is a meaningfully different (and more useful) capability than a
targeted key-recovery attack. A key-recovery attack (e.g. classic
Correlation Power Analysis against AES) requires you to already know quite
a lot about the target — the algorithm, the key schedule, often the
plaintext — and produces a single yes/no outcome for one specific attack.
TVLA is a **black-box leakage scanner**: point it at a device's power
traces, and it tells you whether *any* data-dependent signal exists at all,
without needing to mount a full attack first. That generality is exactly
why it's the industry-standard first-pass test, and exactly why it's a more
interesting thing to build than a single-target attack demo.

**Origin and standing of the method:**
- Goodwill, G., Jun, B., Jaffe, J., & Rohatgi, P. (2011). *A Testing
  Methodology for Side-Channel Resistance Validation* — the original
  proposal of TVLA, presented at the NIST non-invasive attack testing
  workshop (NIAT).
- Becker, G., Cooper, J., DeMulder, E., Goodwill, G., Jaffe, J.,
  Kenworthy, G., Kouzminov, T., Leiserson, A., Marson, M., Rohatgi, P., &
  Saab, S. (2013). *Test Vector Leakage Assessment (TVLA) Methodology in
  Practice* — the widely-cited follow-up formalizing the fixed-vs-random
  Welch's t-test procedure used by this project.
- The method underlies parts of formal side-channel evaluation standards
  such as ISO/IEC 17825.

**Why build a from-scratch version:** proper TVLA tooling is normally
bundled inside expensive commercial evaluation platforms. Most small
hardware makers — the exact people shipping the cheap IoT components this
project cares about — never run this test on their own products because
the tooling and lab equipment are inaccessible. An open, understandable,
from-scratch implementation is a legitimate, useful thing to exist, even
before real hardware capture is wired in.

**Why software-only is a legitimate v1, not a cop-out:** the statistical
core of TVLA (Welch's t-test over sample-aligned trace sets) doesn't care
where the traces came from. Building and rigorously testing that core
against a well-understood synthetic leakage model is real, correct
engineering work, and it de-risks the eventual hardware integration by
making sure the analysis logic is already proven correct before real,
noisy, unpredictable oscilloscope data ever touches it. Be explicit and
honest about this scope in all documentation — do not imply real hardware
was tested when it wasn't.

---

## 3. System Architecture

```
                 ┌────────────────────────┐
 (NOW)           │   Simulated traces      │
                  │  (Hamming-weight leak   │
                  │   model + Gaussian      │
                  │   noise, configurable)  │
                  └───────────┬─────────────┘
                              │
 (LATER, Phase 5+,            │            same interface
  deferred — real             ▼
  oscilloscope /    ┌──────────────────────┐
  ChipWhisperer      │  Trace loader         │  <- io_utils.py already
  captures will       │  (io_utils.py)        │     built now to accept
  plug in here        └───────────┬───────────┘     .npy / .csv trace
  without changing                │                  files, so real
  anything below)                 ▼                  captures drop in
                       ┌──────────────────────┐      later with zero
                       │   TVLA engine          │      changes to the
                       │   (Welch's t-test,      │      engine below.
                       │    fixed-vs-random)     │
                       └───────────┬───────────┘
                                   │
                                   ▼
                       ┌──────────────────────┐
                       │  Report generator      │
                       │  (pass/fail, plots,     │
                       │   "report card" across  │
                       │   multiple profiles)     │
                       └──────────────────────┘
```

The critical architectural decision: **the trace source is abstracted from
day one.** The TVLA engine and report generator never know or care whether
a trace set came from `simulate.py` or from a real oscilloscope capture
file. This is what makes "software only for now, hardware later" an honest,
clean roadmap rather than a rewrite waiting to happen.

---

## 4. The Statistical Core: Welch's t-test (TVLA "Fixed-vs-Random")

### 4.1 Method

1. Collect (or simulate) two groups of traces, each trace being a time
   series of power/voltage samples captured while the device processes one
   input:
   - **Group A ("fixed")**: every trace corresponds to the same fixed
     plaintext/intermediate value.
   - **Group B ("random")**: every trace corresponds to a different,
     uniformly random plaintext/intermediate value.
2. For every time sample index independently, run a **Welch's t-test**
   (a t-test that does not assume equal variance between the two groups —
   important because a device under test can behave differently under
   fixed vs. random inputs even when there's no *secret*-dependent
   leakage) comparing Group A's values at that sample against Group B's
   values at that sample.
3. This produces one t-statistic per time sample — effectively a "leakage
   trace."
4. **Threshold:** `|t| > 4.5` at any sample is the standard, widely-cited
   TVLA pass/fail threshold (corresponds to roughly 99.999% confidence that
   the two distributions differ at that point). If no sample crosses it,
   the implementation passes the test (no detectable leakage at this trace
   count). If any sample crosses it, the device is flagged.

### 4.2 Why this project uses `scipy.stats.ttest_ind(..., equal_var=False)`

This directly implements Welch's t-test with a single, well-tested library
call — no need to hand-roll the variance/pooling math, which is a common
source of subtle bugs in from-scratch implementations. Vectorize the call
across all sample points at once (`axis=0` over shape `(n_traces,
n_samples)` arrays) rather than looping in Python per sample — this matters
once trace lengths grow past a few hundred samples.

---

## 5. Leakage Simulation Module

Until real hardware exists, traces are generated synthetically using the
standard simplified CMOS power-leakage model used throughout the
side-channel literature: power draw at a given instant correlates with the
**Hamming weight** (number of set bits) of the value the device is
processing at that instant, plus Gaussian measurement noise.

```
power(t) = noise(t)  [+ signal_strength × HammingWeight(intermediate_value)   only at the "leaking" sample(s), only if leaky=True]
```

- **`leaky=True` profile** models an unprotected implementation: the sample
  corresponding to the cryptographic operation carries a real,
  data-dependent component.
- **`leaky=False` profile** models a protected implementation (masking,
  constant-time execution, hiding countermeasures): no data-dependent
  component is added anywhere — Group A and Group B should be statistically
  indistinguishable, and the TVLA engine should correctly report "no
  leakage detected."

Configurable parameters: number of traces, number of samples per trace,
which sample index "leaks," signal strength (effectively simulated SNR),
and background noise standard deviation. These parameters let later phases
build a whole family of simulated "device profiles" ranging from
obviously-broken to borderline to clean — see Phase 4 (§7).

**Important honesty note for documentation:** this is a simplified model,
not a hardware-validated one. State clearly in the README that the
simulation is a standard textbook approximation used to validate the
*analysis logic*, not a claim about real device behavior. The value of this
project, before hardware exists, is a correctly-implemented and
well-tested statistical engine — not a claim about real leakage
measurements.

---

## 6. Software Architecture

**Package layout:**

```
snitchwatt/
├── ROADMAP.md                      (this file)
├── README.md                       (written in the documentation phase)
├── LICENSE                         (MIT)
├── requirements.txt                (numpy, scipy, matplotlib, pytest)
├── snitchwatt/
│   ├── __init__.py                 (public API surface)
│   ├── simulate.py                 (§5 — synthetic trace generator)
│   ├── tvla.py                     (§4 — Welch's t-test core + pass/fail eval)
│   ├── report.py                   (plotting + text summary generation)
│   └── io_utils.py                 (load_traces_npy / load_traces_csv — the
│                                     seam where real hardware captures will
│                                     plug in later, unchanged)
├── examples/
│   ├── demo.py                     (end-to-end: simulate leaky + protected
│                                     profiles, run TVLA on both, save plots
│                                     and a printed report)
│   └── output/                     (generated plots/reports land here,
│                                     gitignored except for a couple of
│                                     committed example outputs for the README)
├── benchmark/                      (Phase 4 — "report card" layer)
│   └── run_profiles.py             (runs TVLA across several simulated
│                                     device profiles, outputs a comparison
│                                     table)
└── tests/
    └── test_tvla.py                (pytest — see §8 acceptance criteria)
```

**Core module responsibilities (do not blur these boundaries):**
- `simulate.py` — only produces trace arrays. No statistics, no plotting.
- `tvla.py` — only takes two trace arrays in, returns t-statistics and a
  pass/fail verdict out. No knowledge of where traces came from, no
  plotting.
- `report.py` — only takes `tvla.py`'s output and turns it into a plot
  and/or text summary. No statistics computed here.
- `io_utils.py` — only reads trace files from disk into the same array
  shape `simulate.py` produces. This is what makes swapping in real
  hardware captures later a non-event.

---

## 7. Phased Development Plan

### Phase 0 — Environment Setup (trivial, <1 hour)

**Tasks:** create the package skeleton per §6, set up a virtual environment,
install `numpy`, `scipy`, `matplotlib`, `pytest`.

**Acceptance criterion:** `pip install -r requirements.txt` succeeds and
`import snitchwatt` works with no errors (even with empty stub modules).

---

### Phase 1 — Core TVLA Engine (`tvla.py`) (0.5–1 day)

**Objective:** implement and rigorously test the statistical core before
anything else depends on it.

**Tasks:**
1. Implement `welch_t_test(traces_a, traces_b) -> np.ndarray` using
   `scipy.stats.ttest_ind(traces_a, traces_b, axis=0, equal_var=False)`.
2. Implement `evaluate_leakage(t_stats, threshold=4.5) -> (leaks: bool,
   leak_indices: np.ndarray, max_abs_t: float)`.
3. Define `TVLA_THRESHOLD = 4.5` as a module-level constant, referenced (not
   re-hardcoded) everywhere else it's needed.

**Unit tests to write immediately (do not defer to a later "testing phase"
— this module is trustworthy only if tested now):**
- Two trace sets drawn from **identical** distributions (same mean, same
  variance, no injected leakage) → `evaluate_leakage` must return
  `leaks=False`.
- Two trace sets where one sample index has an obviously large mean
  difference injected → `evaluate_leakage` must return `leaks=True` with
  `leak_indices` containing that sample index.
- Shape/dtype sanity checks (mismatched trace lengths should raise a clear
  error, not fail silently or crash with a cryptic numpy broadcast error).

**Acceptance criterion:** all of the above tests pass under `pytest`.

---

### Phase 2 — Trace Simulation (`simulate.py`) (0.5–1 day)

**Objective:** implement the synthetic leakage model from §5.

**Tasks:**
1. Implement `simulate_traces(n_traces, n_samples, leak_sample, leaky,
   signal_strength, noise_std, seed) -> (traces_fixed, traces_random)` per
   §5.
2. Use `numpy.random.default_rng(seed)` for reproducibility — every example
   and test in this repo should be deterministic given a fixed seed, so
   results in the README are exactly reproducible by anyone who clones it.

**Tests:**
- Output shapes match `(n_traces, n_samples)` for both requested
  parameters.
- With `leaky=True`, running Phase 1's `welch_t_test` +
  `evaluate_leakage` against the output must return `leaks=True`.
- With `leaky=False`, the same pipeline must return `leaks=False`.
  (These two tests are the most important tests in the whole repo — they
  prove the simulator and the analysis engine agree with each other.)

**Acceptance criterion:** the leaky/non-leaky round-trip tests above pass
reliably across multiple random seeds (test at least 3 different seeds per
case to rule out a lucky/unlucky RNG draw).

---

### Phase 3 — Reporting Layer (`report.py`) (0.5 day)

**Objective:** turn raw TVLA output into something a human (or a README)
can read at a glance.

**Tasks:**
1. `plot_tvla(t_stats, title, out_path, threshold=4.5)` — matplotlib plot
   of the t-statistic trace with horizontal threshold lines at ±4.5,
   saved as a PNG.
2. `summarize(name, leaks, leak_indices, max_abs_t) -> str` — short
   human-readable pass/fail text report.
3. `examples/demo.py` — ties Phases 1–3 together end to end: simulate a
   leaky profile and a protected profile, run TVLA on both, save both
   plots to `examples/output/`, print both summaries.

**Acceptance criterion:** running `python examples/demo.py` from a clean
clone produces two PNG plots and two printed summaries, one clearly showing
a threshold crossing (leaky case) and one clearly not (protected case), with
no manual setup beyond `pip install -r requirements.txt`.

---

### Phase 4 — Report-Card Benchmarking Layer (`benchmark/`) (1 day)

**Objective:** until real hardware exists, this phase stands in for "test
multiple real components" by running TVLA across a family of simulated
device profiles with varying characteristics, producing a comparison
table — this is what turns the project from "one demo" into "a benchmarking
tool," which is the more interesting framing.

**Tasks:**
1. Define at least 4 simulated profiles in `benchmark/run_profiles.py`,
   e.g.: `unprotected_high_snr`, `unprotected_low_snr` (borderline —
   important for testing detector sensitivity, not just obvious cases),
   `masked_implementation`, `masked_implementation_with_residual_leak`
   (a masked profile with a small remaining leak — a realistic scenario
   where a countermeasure is imperfect, useful to show the tool catches
   partial leakage too, not just all-or-nothing).
2. Run all profiles through the same TVLA pipeline, collect results into a
   single markdown/CSV table: profile name, pass/fail, max |t|, notes.
3. Save this table into `benchmark/` and reference it from the README.

**Acceptance criterion:** the report-card table correctly distinguishes all
4 profiles as expected (both unprotected profiles flagged, clean masked
profile passes, masked-with-residual-leak profile flagged but with a
visibly smaller max |t| than the fully unprotected profiles — demonstrating
the tool captures *degree* of leakage, not just a binary result).

---

### Phase 5 — Documentation & Portfolio Packaging (1 day)

**Objective:** package this as a standalone, credible GitHub repo entry.

**Tasks:**
1. Write `README.md` (separate from this roadmap): background/motivation
   with the Goodwill 2011 / Becker 2013 TVLA citations (§2), a plain
   explanation of what TVLA is and why it matters, the architecture
   diagram (§3), install/usage instructions, the demo plots embedded
   directly in the README, the Phase 4 report-card table, and an explicit,
   clearly-labeled **"Current Limitations & Roadmap"** section stating: (a)
   this currently runs on simulated traces only, no real hardware has been
   tested yet, and (b) the exact hardware integration plan below (§8) is
   the next step.
2. Add `LICENSE` (MIT).
3. Clean commit history; keep `examples/output/` sample plots committed
   (not gitignored) so the README's embedded images actually render for
   anyone browsing the repo.

**Acceptance criterion:** the README alone, with no other explanation,
lets a reader understand what TVLA is, why this tool is useful even without
hardware yet, and exactly what's simulated vs. real.

---

## 8. Deferred / Future Work — Hardware Integration (out of scope for now)

**Do not build this now.** This section exists so that when hardware
budget is available, a future session can pick this up with full context,
without re-deriving the plan.

- **Capture hardware:** ChipWhisperer-Nano (~$60 / ~₹5,700–8,500 landed in
  India) as the capture tool, paired with a target implementation running
  on an STM32 (e.g. the same Nucleo-L432KC class of board considered for
  the earlier hardware-key project).
- **Integration point:** write a new `capture/` module that talks to the
  ChipWhisperer Python API, captures real trace sets under the same
  fixed-vs-random protocol already implemented, and saves them via the
  *same* `.npy` format `io_utils.py` already reads — meaning the TVLA
  engine, report generator, and benchmarking layer built in Phases 1–4
  require **zero changes** to consume real traces instead of simulated
  ones. This is the entire point of the io_utils abstraction seam in §3.
- **Real-target testing:** once capture works, point it at (a) your own
  firmware with a deliberately unprotected crypto routine, to confirm real
  measured traces get correctly flagged, then (b) a cheap off-the-shelf
  IoT component, to produce the "we found that a ₹300 component fails
  basic leakage testing" result that gives the project real-world
  relevance beyond a self-contained demo.
- **Stretch, source-level leakage mapping:** instrument target firmware
  with timing markers so the tool can report not just "this trace leaks"
  but "the leak happens during this function" — a minimal security linter
  for embedded crypto code. Genuinely underexplored territory even
  academically; attempt only after everything above is solid.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Simulated leakage model is a simplification and may not represent real hardware behavior | State this explicitly and prominently in the README; design the whole architecture (§3) so real traces slot in later with zero changes to the analysis core, once available |
| A too-clean simulated "leaky" profile makes the detector look better than it is (trivially easy to catch obvious leakage, never tested against subtle cases) | Phase 4 explicitly includes a low-SNR / borderline profile and a "masked with residual leak" profile to prove the detector's sensitivity, not just its ability to catch obvious cases |
| Hand-rolled statistics code is a common source of subtle bugs | Use `scipy.stats.ttest_ind` directly rather than reimplementing Welch's t-test by hand; write the round-trip tests in Phase 1/2 before building anything on top |
| Scope creep into building the hardware capture module before the software core is solid | §8 is explicitly marked deferred/future work — do not start it until Phases 0–5 are complete and documented |

---

## 10. References

- Goodwill, G., Jun, B., Jaffe, J., & Rohatgi, P. (2011). *A Testing
  Methodology for Side-Channel Resistance Validation.*
  https://icmconference.org/wp-content/uploads/A16aGoodwilGl.pdf
- Becker, G., Cooper, J., DeMulder, E., Goodwill, G., Jaffe, J.,
  Kenworthy, G., Kouzminov, T., Leiserson, A., Marson, M., Rohatgi, P., &
  Saab, S. (2013). *Test Vector Leakage Assessment (TVLA) Methodology in
  Practice.*
- ISO/IEC 17825 — Testing methods for the mitigation of non-invasive
  attack classes against cryptographic modules (formal standard TVLA-style
  testing feeds into).
- NewAE Technology, ChipWhisperer documentation — reference for the
  deferred hardware capture integration (§8).
- SciPy documentation, `scipy.stats.ttest_ind` — Welch's t-test
  implementation used as the statistical core.
