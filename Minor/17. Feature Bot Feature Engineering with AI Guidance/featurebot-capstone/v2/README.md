# FeatureBot: Feature Engineering with AI Guidance

Industrial capstone project (code **FB-FE-2025-Q3**, Business Intelligence & Analytics). FeatureBot is an AI-guided
feature engineering workflow for the UCI Adult Income dataset: propose features with structured prompts, implement them
behind toggles, evaluate with a leakage-safe pipeline, keep only the winners, and audit fairness.

## Results at a glance

Holdout test set (9,769 rows, stratified 60/20/20 split, seed 42, threshold tuned on validation only):

| Model | AUC | F1 (>50K) |
|---|---|---|
| Baseline logistic regression | 0.904 | 0.689 |
| Enhanced logistic regression (engineered features) | 0.913 | 0.700 |
| Enhanced gradient boosting (features + stronger model) | 0.928 | 0.730 |

Features alone add about +0.9 AUC and +1.1 F1 points to the logistic baseline. The +3 to 5 point F1 target is reached
only when features are combined with gradient boosting (+4.0 F1, +2.4 AUC). The full write-up, including the fairness
audit and trade-offs, is in `docs/FeatureBot_Industrial_Capstone_Project.docx`, and `docs/FeatureBot_Board_Presentation.pptx` is the board presentation.

## Easiest way: double-click (no terminal, no code editor)

1. Install Python 3.9 or newer once from https://www.python.org/downloads/ (tick **Add python.exe to PATH** on Windows).
2. Unzip the project and open the folder in File Explorer.
3. **Windows:** double-click `RUN_FeatureBot.bat`. **Mac:** double-click `RUN_FeatureBot.command`.
4. Wait about 2 minutes (the first run also installs the libraries). A window shows progress, and the results folder
   opens when it finishes.

The launcher sets up a private environment in `.venv`, checks that `adult.csv` is present, runs the main pipeline and
the extended experiments, and saves the results. If Windows says "Windows protected your PC", choose **More info**,
then **Run anyway**. The file is a short plain-text script you can open in Notepad.

## What is adult.csv?

`adult.csv` is the dataset the scripts read: the UCI Adult Income data (48,842 people, 14 predictor columns plus the
`income` target, 15 columns in total). It is `Resources_Dataset.xlsx` saved as a CSV, because pandas and Colab read CSV
files directly and much faster than Excel workbooks.

- It is **included** in this project, so nothing needs to be converted.
- Do not edit or sort it. Missing values are written as `?` and are handled by the code.
- If it is ever lost, put `Resources_Dataset.xlsx` in the same folder and run `prepare_data.py`, or just double-click
  the launcher, which rebuilds it automatically.

## Repository layout

```
featurebot-capstone/
├── README.md
├── requirements.txt
├── .gitignore
├── RUN_FeatureBot.bat                 # Windows: double-click to run everything
├── RUN_FeatureBot.command             # Mac: double-click to run everything
├── adult.csv                          # the dataset (Resources_Dataset.xlsx saved as CSV)
├── prepare_data.py                    # Resources_Dataset.xlsx -> adult.csv
├── featurebot_adult_income.py         # baseline + FeatureBot cycles + holdout report
├── analysis/
│   └── extended_experiments.py        # logistic vs gradient boosting, 5-fold CV
├── docs/
│   ├── HOW_TO_RUN.docx                  # step-by-step run guide with all commands
│   ├── FeatureBot_Industrial_Capstone_Project.docx
│   └── FeatureBot_Board_Presentation.pptx   # 30-slide board deck with clickable agenda
└── results/
    ├── feature_registry.csv           # one row per engineered feature
    ├── experiments_log.csv            # one row per model configuration
    └── extended_experiments.csv       # raw output of analysis/extended_experiments.py
```

## Quick start with commands (optional)

Use this if you prefer a terminal. Requires Python 3.9 or newer.

```bash
# 1. Create an environment and install dependencies
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Only if adult.csv is missing: put Resources_Dataset.xlsx in this folder, then
python prepare_data.py

# 3. Run the FeatureBot pipeline (about 5 seconds)
python featurebot_adult_income.py

# 4. Optional: logistic vs gradient boosting with cross-validation (about 1 minute)
python analysis/extended_experiments.py
```

`adult.csv` ships with the project, so step 2 is normally not needed.

### Running in Google Colab

1. Upload `adult.csv` and `featurebot_adult_income.py` to the Colab working directory.
2. In a cell, run `%run featurebot_adult_income.py`.
3. Download `featurebot_outputs/experiments_log.csv` when it finishes.

## What the script does

1. Loads `adult.csv`, normalises column names, turns `?` into missing values and normalises the target labels
   (including dotted variants such as `>50K.`).
2. Splits the data 60/20/20 with stratification and a fixed seed (42).
3. Builds features through `add_feature_block` with two toggles:
   - **Cycle 1:** capital gain and loss indicators, log transforms, age bins, hours bins, overtime flag, age x education.
   - **Cycle 2:** education buckets, region buckets, marital status x relationship, workclass x hours bin,
     capital gain x education.
4. Fits imputers, scalers and encoders on the training split only, so nothing leaks from validation or test.
5. Picks the decision threshold on the validation set, retrains on train plus validation, and reports once on the holdout.

Expected console output ends with a line like `HOLDOUT  AUC 0.9134  F1 0.7020`.

## Output files

| File | Produced by | Contents |
|---|---|---|
| `featurebot_outputs/experiments_log.csv` | `featurebot_adult_income.py` | Three logistic configurations (baseline, cycle 1, cycle 1+2) on validation |
| `results/extended_experiments.csv` | `analysis/extended_experiments.py` | Logistic and gradient boosting, validation plus 5-fold CV |
| `results/feature_registry.csv` | shipped with the repo | Each feature's definition, type, dependencies, leakage risk, cycle, delta AUC and F1, keep or drop decision |
| `results/experiments_log.csv` | shipped with the repo | The six configurations reported in the document |
| `results/extended_experiments.csv` | `analysis/extended_experiments.py` | Raw output the log above was built from |

The registry deltas are single-feature changes in percentage points on the validation set. Small differences of about
0.001 between the script's output and the document come from the order of columns reaching the solver.

## Fairness

The document reports TPR, FPR, precision, F1 and AUC by sex, race and marital status, and tests two mitigations:
excluding sensitive features, and separate thresholds per sex. Neither is free; the trade-offs are in Section 19 of the
document. Using sex at decision time may not be acceptable in regulated settings, so treat these as options to discuss,
not defaults to deploy.

## Data

UCI Adult Income (Kaggle mirror), 48,842 rows, 14 predictors plus the `income` target. It is a public dataset. The
data file is not committed; regenerate it with `prepare_data.py`.

## Reproducibility checklist

- Fixed seed (42) and stratified splits
- Preprocessing fitted on training data only
- Engineered features are row-wise, so they cannot leak the label
- Threshold chosen on validation, never on the test set
