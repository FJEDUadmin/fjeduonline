# ML Comparison Module (Forensic Chemical Fingerprint)

This repository now includes a starter module for donor/sample comparison based on
chemical profile features (e.g., MRM/Skyline exports).

## Structure

- `ml_comparison_module/schema.py`
  - Metadata validation
  - Skyline table loading
  - Feature engineering (log-ratio with internal standards)
- `ml_comparison_module/pairs.py`
  - Same-donor / different-donor pair generation
  - Pair feature transformation
- `ml_comparison_module/model.py`
  - Pair-based comparison model with probability calibration
  - Donor-wise train/test split to avoid identity leakage
- `ml_comparison_module/metrics.py`
  - ROC summary, Cllr, Tippett-ready coordinates, CMC Top-k
- `ml_comparison_module/demo.py`
  - Synthetic data smoke test (end-to-end)
- `ML_COMPARISON_TIMELINE_ZH.md`
  - 18-month Gantt-style plan aligned with ACS submission target

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ml_comparison_module.demo
```

## Expected use in your project

1. Export MRM quant results from Skyline (`csv`/`tsv`).
2. Ensure metadata columns exist:
   - `sample_id`, `donor_id`, `session_id`, `phase`
3. Build features via `build_feature_matrix`.
4. Train and evaluate with donor-wise split (`donor_wise_train_eval`).
5. Convert calibrated probabilities to LR and report:
   - ROC/AUC
   - Cllr
   - Tippett and CMC
