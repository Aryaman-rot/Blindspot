# ML-Blindspot: Coverage-Directed Test Selection with Verilog Integration

A hardware verification research project that applies **machine learning** to intelligently guide test generation for RTL designs, dramatically reducing the number of tests needed to achieve high coverage.

---

## 🔍 Overview

Traditional hardware verification relies on random or hand-crafted test benches to reach coverage goals — a time-consuming and often incomplete process. **ML-Blindspot** implements a **Coverage-Directed Test Selection (CDS)** pipeline that trains ML classifiers on simulation history to *predict* which test inputs are most likely to cover gaps, then prioritises those tests in the next iteration.

The system is backed by a real **Icarus Verilog** simulation of a priority-encoder RTL module, making this a genuine hardware-in-the-loop ML experiment rather than a pure software simulation.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      main.py (CLI)                      │
│  --seed  --classifier  --compare  --iterations  etc.   │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │      exp.py         │
              │  Experiment runner  │
              │  CDS vs. Random     │
              └──────┬──────┬───────┘
                     │      │
          ┌──────────▼─┐  ┌─▼──────────────┐
          │   cds.py   │  │   tests.py      │
          │ ML Selector│  │ Test Simulator  │
          │ RF / GB    │  │ Coverage Oracle │
          └──────┬─────┘  └──────┬──────────┘
                 │               │
          ┌──────▼───────────────▼──────┐
          │           dut.py            │
          │     SimpleDUT (Python)      │
          │  + Verilog co-simulation    │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │     rtl/signal_proc.v       │
          │  Priority Encoder (Verilog) │
          │  Simulated via iverilog/vvp │
          └─────────────────────────────┘
```

---

## 📦 Components

| File | Role |
|---|---|
| `main.py` | CLI entry point — configures and launches experiments |
| `exp.py` | `Experiment` class — orchestrates CDS vs. random selection runs |
| `cds.py` | `CoverageDirectedTestSelection` — trains classifiers per coverage group and selects the next best tests |
| `dut.py` | `SimpleDUT` — defines coverage groups (GROUP1–4) and drives Verilog simulation |
| `tests.py` | `TestSimulator` — runs tests, maps Verilog outputs to Python coverage IDs |
| `rtl/signal_proc.v` | Synthesisable Verilog priority encoder with bypass/process modes |
| `rtl/signal_proc_tb.v` | Testbench — reads `stimulus.csv`, writes `sim_output.csv` |
| `requirements.txt` | Python dependencies |

---

## 🧠 Coverage Groups

The DUT models a 5-input signal processor with **57 coverage points** across 4 groups:

| Group | Description | Points |
|---|---|---|
| **GROUP1** | MEM-path (`input_interface=0`) combinations of data_size × output_active × data_bin | 24 |
| **GROUP2** | Radar-path (`input_interface=1`) combinations of data_size × output_active × data_bin | 24 |
| **GROUP3** | Special high-bin Radar case (`data_bin > 5000`) | 1 |
| **GROUP4** | Bypass mode (`data_mode=0`) coverage — all interface × output_active × bin combos | 8 |

### Cross-field Gating Rule (Process Mode)
In Process Mode (`data_mode=1`), if `input_interface=1` (Radar), `data_size=4`, and `output_active=0`, the Verilog gates `encoded_out` to `2'b00` — meaning those GROUP2 points can **only** be reached via the Bypass Mode path (`data_mode=0`). This tests the ML's ability to discover non-obvious cross-field constraints.

---

## ⚙️ Input Fields

| Field | Values | Notes |
|---|---|---|
| `data_mode` | 0, 1 | 0 = Bypass, 1 = Process |
| `input_interface` | 0, 1 | 0 = MEM, 1 = Radar |
| `data_size` | 1, 2, 3, 4 | Maps to Verilog 2-bit value (`data_size - 1`) |
| `output_active` | 0, 1 | Output enable |
| `data_bin` | 0–10000 | 14-bit value; split into ranges per coverage group |

---

## 🤖 ML Pipeline

1. **Initial Phase**: Run `N` random tests to seed the coverage database.
2. **CDS Iterations**: For each uncovered coverage group:
   - Extract positive examples (tests that hit the group) and negative examples.
   - Train a **Random Forest** or **Gradient Boosting** classifier using the full dataset with `class_weight='balanced'` to handle class imbalance without discarding data.
   - Score all candidate tests using `predict_proba`, and select the highest-scoring test to run next.
3. **Feature Importances**: After the final iteration, print the learned feature importances per group to interpret what the model found most predictive.

### Classifiers

| Flag | Model |
|---|---|
| `--classifier rf` | `RandomForestClassifier` with `class_weight='balanced'` (default) |
| `--classifier gb` | `GradientBoostingClassifier` with balanced sample weights |
| `--compare` | Evaluates both on an 80/20 train/val split and prints Accuracy, Recall, F1 |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Icarus Verilog](https://bleyer.org/icarus/) installed (ensure `iverilog` and `vvp` are on `PATH`, or installed at `C:\iverilog\bin\` on Windows)

### Install Dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### Run Experiments

```bash
# Default run (100 CDS iterations, seed 42)
python main.py --seed 42

# Short run for quick testing
python main.py --seed 42 --initial-tests 50 --iterations 5 --tests-per-iter 10

# Use Gradient Boosting classifier
python main.py --seed 42 --classifier gb

# Compare RF vs GB on current data
python main.py --seed 42 --compare --initial-tests 50

# Show feature importances at every iteration
python main.py --seed 42 --show-importances

# Save coverage plot
python main.py --seed 42 --show
```

---

## 📊 Sample Results

CDS achieves **significant test savings** over pure random selection:

| Coverage Target | CDS Tests | Random Tests | Savings |
|---|---|---|---|
| 90% | ~1,500 | ~5,500 | **~73%** |
| 95% | ~2,400 | ~5,500 | **~56%** |
| 98% | ~3,700 | ~5,500 | **~33%** |

---

## 🔬 Verilog Integration Details

- `dut.py` writes `stimulus.csv` (one test vector per row), invokes `iverilog` to compile `signal_proc.v` + `signal_proc_tb.v`, runs `vvp`, and reads `sim_output.csv`.
- Compilation is **cached**: the `.vvp` binary is only recompiled when the `.v` source files change (file mtime check, similar to `make`).
- On Windows, fallback paths to `C:\iverilog\bin\iverilog` and `C:\iverilog\bin\vvp` are used automatically if the tools are not on `PATH`.

---

## 📋 Requirements

```
numpy
pandas
matplotlib
scikit-learn
```

---

## 📄 License

MIT
