# featurebot_adult_income.py
# Project: FeatureBot - AI-Guided Feature Engineering for UCI Adult Income (FB-FE-2025-Q3)
# Tools: Google Colab, Python (pandas, numpy, scikit-learn, category_encoders)
# Skills: Feature Engineering, Prompting (ChatGPT / an AI assistant is used OUTSIDE this script;
#         the prompts and the recorded responses are stored in this file and in the outputs folder)
#
# How to run (Colab):
#   1. Upload adult.csv to the Colab working directory (or adjust DATA_PATH).
#   2. Create this file, paste the script, save.
#   3. %run featurebot_adult_income.py          -> runs baseline + FeatureBot cycles + final report
#      or: import featurebot_adult_income as fb ; fb.run_pipeline()
#   4. Outputs (feature_registry.csv, experiments_log.csv, ...) are written to ./featurebot_outputs
#
# Design rules (from the project document): fixed seeds, stratified 60/20/20 split,
# imputers / encoders / scalers fitted on TRAIN ONLY (they live inside sklearn Pipelines),
# no data leakage, selection decisions read CV results only (never the holdout).

# %% 1. Setup & data load
import os, sys, time, json, warnings, subprocess
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
try:
    get_ipython()  # noqa  (inside Colab / Jupyter keep the inline backend)
except NameError:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import category_encoders as ce
except ImportError:  # Colab usually needs this once
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "category_encoders"])
    import category_encoders as ce

from sklearn.base import clone
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
                             precision_recall_fscore_support, precision_recall_curve,
                             roc_curve, confusion_matrix, classification_report)

SEED = 42
N_FOLDS = 5
DATA_PATH = next((p for p in ["adult.csv", "/content/adult.csv"] if os.path.exists(p)), "adult.csv")
OUT_DIR = "featurebot_outputs"
FIG_DIR = os.path.join(OUT_DIR, "figures")
NUMERIC_RAW = ["age", "fnlwgt", "educational_num", "capital_gain", "capital_loss", "hours_per_week"]
SENSITIVE = ["gender", "race", "marital_status"]      # the PDF's "sex" is the `gender` column in adult.csv
MIN_GROUP_N = 50                                       # subgroups smaller than this are flagged in parity ratios

# Decision rule used when pruning features (CV on the TRAIN split only)
KEEP_MIN_DAUC, KEEP_MIN_DF1, KEEP_MIN_FOLDS = 0.0005, 0.003, 4
FAIRNESS_TPR_GAP_TOL = 0.01                            # max allowed widening of the gender TPR gap

DATA, LOG, CACHE, CONFIG_ROWS = {}, [], {}, {}


def reset_state():
    DATA.clear(); LOG.clear(); CACHE.clear(); CONFIG_ROWS.clear()


def show(obj, title=None):
    if title:
        print("\n" + title)
    try:
        from IPython.display import display
        display(obj)
    except Exception:
        print(obj.to_string() if hasattr(obj, "to_string") else obj)


def save_csv(df, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(os.path.join(OUT_DIR, name), index=False)


def save_fig(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, name), dpi=130, bbox_inches="tight")
    plt.show(); plt.close(fig)


def load_data(path=DATA_PATH):
    """Load adult.csv, normalise names/labels, '?' -> NaN, validate (rules from the data dictionary)."""
    raw = pd.read_csv(path)
    df = raw.copy()
    df.columns = [c.strip().lower().replace("-", "_") for c in df.columns]
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].astype(object).where(df[c].notna(), np.nan)
            df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)
    q_counts = {c: int((df[c] == "?").sum()) for c in ["workclass", "occupation", "native_country"]}
    df = df.replace("?", np.nan)                                     # "?" -> NaN before encoding
    raw_labels = sorted(df["income"].astype(str).str.strip().unique())
    dotted = int(df["income"].astype(str).str.strip().str.endswith(".").sum())
    df["income"] = df["income"].astype(str).str.strip().str.rstrip(".").map({">50K": 1, "<=50K": 0})
    for c in NUMERIC_RAW:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    dq = []
    def add(check, rule, ok, detail):
        dq.append({"check": check, "rule": rule, "result": "PASS" if ok else "FAIL", "detail": detail})
    add("Rows / columns", "adult.csv has 15 columns", df.shape[1] == 15, f"{df.shape[0]} rows x {df.shape[1]} columns")
    add("Column names normalised", "strip, lower-case, '-' -> '_'", True, ", ".join(df.columns))
    add("Type enforcement", "age, fnlwgt, educational_num, capital_gain, capital_loss, hours_per_week numeric",
        all(pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().all() for c in NUMERIC_RAW), "all six columns numeric, no coercion failures")
    add("Missing '?' handled", "'?' -> NaN in workclass, occupation, native_country", True,
        "; ".join(f"{k}: {v} '?' replaced" for k, v in q_counts.items()))
    add("Target labels normalised", "dotted variants '>50K.' / '<=50K.' mapped; binary 0/1", df["income"].isin([0, 1]).all(),
        f"raw labels {raw_labels}; dotted variants found: {dotted}; mapped to {{<=50K:0, >50K:1}}")
    add("Range: age", "16 <= age <= 100", bool(df["age"].between(16, 100).all()), f"violations: {int((~df['age'].between(16, 100)).sum())} (min {df['age'].min()}, max {df['age'].max()})")
    add("Range: hours_per_week", "0 <= hours_per_week <= 100", bool(df["hours_per_week"].between(0, 100).all()), f"violations: {int((~df['hours_per_week'].between(0, 100)).sum())} (min {df['hours_per_week'].min()}, max {df['hours_per_week'].max()})")
    add("Range: capital_gain", "capital_gain >= 0", bool((df["capital_gain"] >= 0).all()), f"violations: {int((df['capital_gain'] < 0).sum())}")
    add("Range: capital_loss", "capital_loss >= 0", bool((df["capital_loss"] >= 0).all()), f"violations: {int((df['capital_loss'] < 0).sum())}")
    add("Remaining missing values", "imputed inside the pipeline (train-only): categorical most frequent, numeric median", True,
        "; ".join(f"{c}: {int(df[c].isna().sum())}" for c in df.columns if df[c].isna().any()))
    return df, pd.DataFrame(dq)


def split_data(df):
    """Stratified 60/20/20 split, fixed seed."""
    y = df["income"].astype(int); X = df.drop(columns="income")
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.40, stratify=y, random_state=SEED)
    X_val, X_te, y_val, y_te = train_test_split(X_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=SEED)
    for n, a in dict(X_train=X_tr, X_val=X_val, X_test=X_te).items():
        DATA[n] = a.reset_index(drop=True)
    for n, a in dict(y_train=y_tr, y_val=y_val, y_test=y_te).items():
        DATA[n] = a.reset_index(drop=True)
    return (DATA["X_train"], DATA["X_val"], DATA["X_test"], DATA["y_train"], DATA["y_val"], DATA["y_test"])


def split_checks():
    n = sum(len(DATA[k]) for k in ["y_train", "y_val", "y_test"])
    rows = []
    for k in ["train", "val", "test"]:
        y = DATA["y_" + k]
        rows.append({"check": f"Split: {k}", "rule": "stratified 60/20/20, seed 42", "result": "PASS" if abs(len(y) / n - {"train": .6, "val": .2, "test": .2}[k]) < 0.005 else "FAIL",
                     "detail": f"{len(y)} rows ({len(y) / n:.1%}); >50K rate {y.mean():.3f}"})
    rows.append({"check": "Leakage control", "rule": "imputers / encoders / scalers fitted on train only", "result": "PASS",
                 "detail": "all preprocessing and target/frequency encoders live inside sklearn Pipelines fitted on the training rows of each fold"})
    rows.append({"check": "Holdout integrity", "rule": "selection decisions never read the holdout", "result": "PASS",
                 "detail": "keep/prune decisions use 5-fold CV on train only; holdout metrics are logged for stability monitoring"})
    return pd.DataFrame(rows)

# %% 2. EDA summary
def eda_summary(X_train, y_train):
    """EDA on the TRAINING split only (value counts, missingness matrix, class balance, distributions / skew)."""
    d = X_train.copy(); d["income"] = y_train.values
    rows = []
    for c in d.columns:
        s = d[c]
        top = s.value_counts(dropna=True)
        rows.append({"column": c, "dtype": "numeric" if pd.api.types.is_numeric_dtype(s) else "categorical",
                     "n_unique": int(s.nunique()), "n_missing": int(s.isna().sum()), "pct_missing": round(100 * s.isna().mean(), 2),
                     "skew": round(float(s.skew()), 3) if pd.api.types.is_numeric_dtype(s) else np.nan,
                     "top_value": str(top.index[0]) if len(top) else "", "top_value_share": round(float(top.iloc[0] / len(s)), 3) if len(top) else np.nan})
    eda = pd.DataFrame(rows)
    show(eda, "EDA summary (train split)")
    print("\nClass balance (train):\n", y_train.value_counts(normalize=True).rename({0: "<=50K", 1: ">50K"}).round(3).to_string())
    for col in [c for c in X_train.columns if not pd.api.types.is_numeric_dtype(X_train[c])]:
        print(f"\n{col} value counts (top 8, incl. missing):\n", X_train[col].value_counts(dropna=False).head(8).to_string())
    fig, ax = plt.subplots(figsize=(10, 3.8))
    samp = d.drop(columns="income").sample(400, random_state=SEED)
    ax.imshow(samp.isna().values.T, aspect="auto", cmap="gray_r", interpolation="nearest")
    ax.set_yticks(range(samp.shape[1])); ax.set_yticklabels(samp.columns, fontsize=8); ax.set_xlabel("400 random training rows")
    ax.set_title("Missingness matrix (dark = missing)"); save_fig(fig, "eda_missingness_matrix.png")
    fig, ax = plt.subplots(figsize=(4.5, 3.4))
    vc = y_train.value_counts(normalize=True).sort_index()
    ax.bar(["<=50K", ">50K"], vc.values, color=["#E8833A", "#2F6DB5"]); ax.set_ylabel("share of rows"); ax.set_title("Class balance (train)")
    for i, v in enumerate(vc.values): ax.text(i, v + 0.01, f"{v:.1%}", ha="center")
    save_fig(fig, "eda_class_balance.png")
    num = [c for c in NUMERIC_RAW]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6))
    for a, c in zip(axes.ravel(), num):
        a.hist(X_train[c], bins=30, color="#2F6DB5"); a.set_title(f"{c} (skew {X_train[c].skew():.2f})", fontsize=10)
    fig.suptitle("Numeric distributions (train)"); save_fig(fig, "eda_numeric_distributions.png")
    save_csv(eda, "eda_summary.csv")
    return eda

# %% 3. Feature block (toggles), feature specs and AI responses
EDU_GROUP = {**{k: "HS-or-less" for k in ["Preschool", "1st-4th", "5th-6th", "7th-8th", "9th", "10th", "11th", "12th", "HS-grad"]},
             **{k: "Some-College" for k in ["Some-college", "Assoc-voc", "Assoc-acdm"]}, "Bachelors": "Bachelors",
             **{k: "Advanced" for k in ["Masters", "Prof-school", "Doctorate"]}}
AMERICAS = ["United-States", "Canada", "Mexico", "Puerto-Rico", "Cuba", "Jamaica", "Dominican-Republic", "Haiti", "Guatemala",
            "Honduras", "El-Salvador", "Nicaragua", "Columbia", "Ecuador", "Peru", "Trinadad&Tobago"]
EUROPE = ["England", "Germany", "Italy", "Poland", "Portugal", "France", "Greece", "Ireland", "Hungary", "Scotland", "Yugoslavia", "Holand-Netherlands"]
ASIA = ["India", "Japan", "China", "Iran", "Philippines", "Vietnam", "Taiwan", "Hong", "Laos", "Thailand", "Cambodia"]
REGION = {**{k: "Americas" for k in AMERICAS}, **{k: "Europe" for k in EUROPE}, **{k: "Asia" for k in ASIA}}


def _cross(a, b):
    return a.fillna("Unknown").astype(str) + "_x_" + b.fillna("Unknown").astype(str)


def add_feature_block(df, toggles=(), drop_cols=()):
    """Row-wise (stateless, target-free) feature block. `toggles` = feature keys to switch on.
    Features that must be FITTED (occupation_catboost, native_country_freq) are added inside the sklearn pipeline."""
    t = set(toggles); d = df.copy()
    gain_gt0 = (d["capital_gain"].fillna(0) > 0).astype(int)
    hbin = pd.cut(d["hours_per_week"], bins=[-1, 30, 40, 50, 1000], labels=["<=30", "31-40", "41-50", "51+"]).astype(object)
    if "capital_gain_gt0" in t: d["capital_gain_gt0"] = gain_gt0
    if "capital_loss_gt0" in t: d["capital_loss_gt0"] = (d["capital_loss"].fillna(0) > 0).astype(int)
    if "overtime" in t: d["overtime"] = (d["hours_per_week"] > 40).astype(int)
    if "capital_gain_log" in t: d["capital_gain_log"] = np.log1p(d["capital_gain"].fillna(0))
    if "capital_loss_log" in t: d["capital_loss_log"] = np.log1p(d["capital_loss"].fillna(0))
    if "fnlwgt_log" in t: d["fnlwgt_log"] = np.log1p(d["fnlwgt"])
    if "age_bin" in t: d["age_bin"] = pd.cut(d["age"], bins=[0, 25, 35, 45, 55, 200], labels=["<=25", "26-35", "36-45", "46-55", "56+"]).astype(object)
    if "hours_bin" in t: d["hours_bin"] = hbin
    if "age_x_education_num" in t: d["age_x_education_num"] = d["age"] * d["educational_num"]
    if "education_group" in t: d["education_group"] = d["education"].map(EDU_GROUP)
    if "native_region" in t: d["native_region"] = d["native_country"].map(REGION).fillna("Other")
    if "marital_x_relationship" in t: d["marital_x_relationship"] = _cross(d["marital_status"], d["relationship"])
    if "gain_gt0_x_occupation" in t: d["gain_gt0_x_occupation"] = _cross(gain_gt0.astype(str), d["occupation"])
    if "occupation_x_hours_bin" in t: d["occupation_x_hours_bin"] = _cross(d["occupation"], hbin)
    if "workclass_x_hours_bin" in t: d["workclass_x_hours_bin"] = _cross(d["workclass"], hbin)
    if "gender_x_occupation" in t: d["gender_x_occupation"] = _cross(d["gender"], d["occupation"])
    d = d.drop(columns=[c for c in drop_cols if c in d.columns])
    for c in d.columns:
        if not pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].astype(object)
    return d


def _spec(key, cycle, prompt, group, ftype, definition, deps, leak, why, code, fair=""):
    return dict(key=key, cycle=cycle, prompt=prompt, group=group, type=ftype, definition=definition, dependencies=deps,
                leakage_risk=leak, rationale=why, pseudocode=code, fairness_note=fair)

NOLEAK = "None - row-wise function of raw columns, target never used"
SPECS = [
    # ---- Cycle 1, Template A, invocation A-1
    _spec("capital_gain_gt0", 1, "A-1", "indicators", "binary indicator", "1 if capital_gain > 0 else 0", "capital_gain", NOLEAK,
          "Handles sparsity; flags non-zero gains.", "df['capital_gain_gt0'] = (df['capital_gain'] > 0).astype(int)"),
    _spec("capital_loss_gt0", 1, "A-1", "indicators", "binary indicator", "1 if capital_loss > 0 else 0", "capital_loss", NOLEAK,
          "Same sparsity argument for losses; loss filers differ from non-filers.", "df['capital_loss_gt0'] = (df['capital_loss'] > 0).astype(int)"),
    _spec("capital_gain_log", 1, "A-1", "log_transforms", "numeric transform", "log1p(capital_gain)", "capital_gain", NOLEAK,
          "Heavily skewed; log1p compresses the 99999 tail for a linear model.", "df['capital_gain_log'] = np.log1p(df['capital_gain'])"),
    _spec("capital_loss_log", 1, "A-1", "log_transforms", "numeric transform", "log1p(capital_loss)", "capital_loss", NOLEAK,
          "Heavily skewed; log1p compresses the tail.", "df['capital_loss_log'] = np.log1p(df['capital_loss'])"),
    _spec("fnlwgt_log", 1, "A-1", "log_transforms", "numeric transform", "log1p(fnlwgt)", "fnlwgt", NOLEAK,
          "Census weight is right-skewed; log1p symmetrises it.", "df['fnlwgt_log'] = np.log1p(df['fnlwgt'])"),
    _spec("age_bin", 1, "A-1", "bins", "categorical bin", "age bins: <=25, 26-35, 36-45, 46-55, 56+", "age", NOLEAK,
          "Captures nonlinearity for linear models.", "df['age_bin'] = pd.cut(df['age'], [0,25,35,45,55,200], labels=['<=25','26-35','36-45','46-55','56+'])"),
    _spec("hours_bin", 1, "A-1", "bins", "categorical bin", "hours-per-week bins: <=30, 31-40, 41-50, 51+", "hours_per_week", NOLEAK,
          "Overtime signal; stronger separation.", "df['hours_bin'] = pd.cut(df['hours_per_week'], [-1,30,40,50,1000], labels=['<=30','31-40','41-50','51+'])"),
    # ---- Cycle 1, Template A, invocation A-2
    _spec("overtime", 1, "A-2", "indicators", "binary indicator", "1 if hours_per_week > 40 else 0", "hours_per_week", NOLEAK,
          "Explicit overtime flag (simple, stable).", "df['overtime'] = (df['hours_per_week'] > 40).astype(int)"),
    _spec("age_x_education_num", 1, "A-2", "age_x_education", "numeric interaction", "age * educational_num", "age, educational_num", NOLEAK,
          "Seniority / skill proxy.", "df['age_x_education_num'] = df['age'] * df['educational_num']"),
    _spec("education_group", 1, "A-2", "groupings", "categorical grouping", "education buckets: HS-or-less, Some-College, Bachelors, Advanced", "education", NOLEAK,
          "Collapses 16 education levels to 4 stable buckets.", "df['education_group'] = df['education'].map(EDU_GROUP)"),
    _spec("native_region", 1, "A-2", "groupings", "categorical grouping", "native-country buckets: Americas, Europe, Asia, Other (missing -> Other)", "native_country", NOLEAK,
          "42 sparse countries -> 4 regions; reduces noise.", "df['native_region'] = df['native_country'].map(REGION).fillna('Other')"),
    _spec("occupation_catboost", 1, "A-2", "encodings", "encoding (target, ordered)", "CatBoost (ordered target statistics) encoding of occupation, fitted inside the pipeline on train rows only",
          "occupation, income (train only)", "Medium by nature (uses target) - mitigated: ordered statistics, fitted inside each CV fold's training rows only",
          "Medium-cardinality column; one number instead of 15 dummies.", "enc = ce.CatBoostEncoder(cols=['occupation']); X_tr['occupation_te'] = enc.fit_transform(X_tr, y_tr)['occupation']; X_va = enc.transform(X_va)"),
    _spec("native_country_freq", 1, "A-2", "encodings", "encoding (frequency)", "normalised frequency of native_country, fitted inside the pipeline on train rows only",
          "native_country (train only)", "Low - target never used; counts fitted on train rows only",
          "High-cardinality column; frequency separates the dominant country from rare ones.", "enc = ce.CountEncoder(cols=['native_country'], normalize=True); enc.fit(X_tr)"),
    # ---- Cycle 2, Template B, invocation B-1 (3 interactions to reduce false negatives)
    _spec("marital_x_relationship", 2, "B-1", "interactions", "categorical interaction", "marital_status x relationship (42 possible levels)", "marital_status, relationship", NOLEAK,
          "Married-civ-spouse heads of household are the largest group of missed >50K earners.", "df['marital_x_relationship'] = df['marital_status'] + '_x_' + df['relationship']",
          "marital_status is a sensitive attribute - the cross inherits it; audit TPR gap by marital_status."),
    _spec("gain_gt0_x_occupation", 2, "B-1", "interactions", "categorical interaction", "capital_gain_gt0 x occupation", "capital_gain, occupation", NOLEAK,
          "A capital gain means something different in Exec-managerial than in Other-service.", "df['gain_gt0_x_occupation'] = (df['capital_gain']>0).astype(str) + '_x_' + df['occupation'].fillna('Unknown')",
          "occupation correlates with gender; low direct risk, audit gender TPR gap."),
    _spec("occupation_x_hours_bin", 2, "B-1", "interactions", "categorical interaction", "occupation x hours-per-week bin (hours-per-week x occupation)", "occupation, hours_per_week", NOLEAK,
          "Long hours pay off differently by occupation.", "df['occupation_x_hours_bin'] = df['occupation'].fillna('Unknown') + '_x_' + hours_bin",
          "Low risk; audit gender TPR gap."),
    # ---- Cycle 2, Template B, invocation B-2
    _spec("workclass_x_hours_bin", 2, "B-2", "interactions", "categorical interaction", "workclass x hours-per-week bin", "workclass, hours_per_week", NOLEAK,
          "Self-employed long-hours workers differ from salaried ones.", "df['workclass_x_hours_bin'] = df['workclass'].fillna('Unknown') + '_x_' + hours_bin",
          "Low risk."),
    _spec("gender_x_occupation", 2, "B-2", "interactions", "categorical interaction", "gender x occupation (sex x occupation)", "gender, occupation", NOLEAK,
          "Occupational pay structure may differ by gender.", "df['gender_x_occupation'] = df['gender'] + '_x_' + df['occupation'].fillna('Unknown')",
          "Direct sensitive-attribute interaction - HIGHEST fairness risk; audited for the gender TPR gap before it can be kept.", ),
]
SPEC_BY_KEY = {s["key"]: s for s in SPECS}
KEYS_C1 = [s["key"] for s in SPECS if s["cycle"] == 1]
KEYS_C2 = [s["key"] for s in SPECS if s["cycle"] == 2]
FAIRNESS_AUDITED = {"gender_x_occupation", "marital_x_relationship"}
ENCODER_KEYS = {"occupation_catboost", "native_country_freq"}
DERIVED_SENSITIVE = ["marital_x_relationship", "gender_x_occupation"]   # crosses that contain a sensitive column

TEMPLATE_A = "Given schema + EDA [paste], propose 5 transformations with rationale, leakage risk, and pandas pseudocode; optimize for F1 on >50K."
TEMPLATE_B = "Given validation errors [paste], suggest 3 interactions to reduce false negatives; provide code and fairness notes."
TEMPLATE_C = "Given subgroup metrics [paste], propose mitigations with minimal overall F1 loss; include steps."


def build_prompt(template, context):
    return template.replace("[paste]", "\n----- pasted context -----\n" + context + "\n----- end of pasted context -----\n")


def format_response(prompt_id):
    out = []
    for i, s in enumerate([s for s in SPECS if s["prompt"] == prompt_id], 1):
        out.append(f"{i}. {s['key']}  [{s['type']}]\n   Rationale: {s['rationale']}\n   Leakage risk: {s['leakage_risk']}\n   Pandas pseudocode: {s['pseudocode']}" +
                   (f"\n   Fairness note: {s['fairness_note']}" if s["fairness_note"] else ""))
    return "\n".join(out)

# %% 4. Pipelines, metrics, experiment tracking
def make_model(name):
    if name == "lr":
        return LogisticRegression(penalty="l2", max_iter=2000, random_state=SEED)
    if name == "rf":
        return RandomForestClassifier(n_estimators=100, min_samples_leaf=3, n_jobs=-1, random_state=SEED)
    if name == "gb":
        return HistGradientBoostingClassifier(max_iter=150, random_state=SEED)
    if name == "xgb":
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, eval_metric="logloss", random_state=SEED, n_jobs=2, verbosity=0)
    if name == "lgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=200, learning_rate=0.1, random_state=SEED, verbose=-1, n_jobs=2)
    raise ValueError(name)

MODEL_LABEL = {"lr": "Logistic Regression (L2)", "rf": "Random Forest", "gb": "Gradient Boosting (HistGB)", "xgb": "XGBoost", "lgbm": "LightGBM"}


def available_models():
    out = ["lr", "rf", "gb"]
    for n, mod in [("xgb", "xgboost"), ("lgbm", "lightgbm")]:
        try:
            __import__(mod); out.append(n)
        except Exception:
            pass
    return out


def build_pipeline(toggles=(), model="lr", drop_cols=()):
    t = tuple(sorted(toggles)); dc = tuple(drop_cols)
    sample = add_feature_block(DATA["X_train"].head(300), t, dc)
    num_cols = [c for c in sample.columns if pd.api.types.is_numeric_dtype(sample[c])]
    cat_cols = [c for c in sample.columns if c not in num_cols]
    parts = [("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num_cols),
             ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("ohe", OneHotEncoder(handle_unknown="ignore"))]), cat_cols)]
    if "occupation_catboost" in t and "occupation" in sample.columns:
        parts.append(("occ_cb", Pipeline([("enc", ce.CatBoostEncoder(cols=["occupation"], handle_missing="value", handle_unknown="value")), ("scaler", StandardScaler())]), ["occupation"]))
    if "native_country_freq" in t and "native_country" in sample.columns:
        parts.append(("nat_freq", Pipeline([("enc", ce.CountEncoder(cols=["native_country"], normalize=True, handle_missing="value", handle_unknown="value")), ("scaler", StandardScaler())]), ["native_country"]))
    fe = FunctionTransformer(add_feature_block, kw_args={"toggles": t, "drop_cols": dc}, validate=False)
    return Pipeline([("fe", fe), ("prep", ColumnTransformer(parts, sparse_threshold=0)), ("clf", make_model(model))])


def best_f1_threshold(y, p):
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / (prec + rec + 1e-12)
    return float(thr[int(np.nanargmax(f1[:-1]))])


def compute_metrics(y, p, thr=0.5):
    y = np.asarray(y); pred = (np.asarray(p) >= thr).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"AUC": roc_auc_score(y, p), "PR_AUC": average_precision_score(y, p), "F1": f1, "Precision": prec, "Recall": rec,
            "Brier": brier_score_loss(y, p), "threshold": thr, "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)}


def report_metrics(y_true, y_pred, y_prob):
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    auc = roc_auc_score(y_true, y_prob)
    print(f"AUC: {auc:.3f} | F1: {f1:.3f} | Precision: {prec:.3f} | Recall: {rec:.3f}")
    return {"AUC": auc, "F1": f1, "Precision": prec, "Recall": rec}


def features_summary(toggles):
    if not toggles:
        return "baseline (raw columns only)"
    order = [s["key"] for s in SPECS if s["key"] in toggles]
    return f"{len(order)} features: " + ", ".join(order)


def evaluate_config(config_id, toggles=(), model="lr", drop_cols=(), comments="", log=True):
    """5-fold stratified CV on TRAIN, then fit on train -> validation (threshold tuned on validation) -> holdout (logged only)."""
    key = (tuple(sorted(toggles)), model, tuple(sorted(drop_cols)))
    if key in CACHE:
        hit = CACHE[key]
        if log and config_id not in CONFIG_ROWS and hit["config_id"] in CONFIG_ROWS:   # same configuration under a new ID: log an alias row, no recompute
            row = dict(LOG[CONFIG_ROWS[hit["config_id"]]])
            row.update({"config_id": config_id, "runtime_sec": 0.0, "comments": (comments + " | " if comments else "") + f"identical configuration to {hit['config_id']} (result reused, not recomputed)"})
            CONFIG_ROWS[config_id] = len(LOG); LOG.append(row)
        return hit
    t0 = time.time(); X, y = DATA["X_train"], DATA["y_train"]
    skf = StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED)
    aucs, f1s, aps = [], [], []
    for tr, va in skf.split(X, y):
        pipe = build_pipeline(toggles, model, drop_cols).fit(X.iloc[tr], y.iloc[tr])
        p = pipe.predict_proba(X.iloc[va])[:, 1]
        m = compute_metrics(y.iloc[va], p, 0.5)
        aucs.append(m["AUC"]); f1s.append(m["F1"]); aps.append(m["PR_AUC"])
    pipe = build_pipeline(toggles, model, drop_cols).fit(X, y)
    p_val = pipe.predict_proba(DATA["X_val"])[:, 1]; p_test = pipe.predict_proba(DATA["X_test"])[:, 1]
    thr = best_f1_threshold(DATA["y_val"], p_val)
    res = {"config_id": config_id, "toggles": tuple(sorted(toggles)), "model": model, "drop_cols": tuple(drop_cols), "pipe": pipe,
           "cv_auc": np.array(aucs), "cv_f1": np.array(f1s), "cv_ap": np.array(aps), "threshold": thr,
           "p_val": p_val, "p_test": p_test, "val": compute_metrics(DATA["y_val"], p_val, thr), "val_05": compute_metrics(DATA["y_val"], p_val, 0.5),
           "test": compute_metrics(DATA["y_test"], p_test, thr), "test_05": compute_metrics(DATA["y_test"], p_test, 0.5), "runtime": time.time() - t0}
    CACHE[key] = res
    if log:
        CONFIG_ROWS[config_id] = len(LOG)
        LOG.append({"config_id": config_id, "features_enabled": features_summary(toggles) + (f"; dropped columns: {', '.join(drop_cols)}" if drop_cols else ""),
                    "model": MODEL_LABEL[model], "cv_auc_mean": round(res["cv_auc"].mean(), 4), "cv_auc_std": round(res["cv_auc"].std(), 4),
                    "cv_f1_mean": round(res["cv_f1"].mean(), 4), "cv_f1_std": round(res["cv_f1"].std(), 4),
                    "val_auc": round(res["val"]["AUC"], 4), "val_f1": round(res["val"]["F1"], 4), "val_threshold": round(thr, 3),
                    "holdout_auc": round(res["test"]["AUC"], 4), "holdout_f1": round(res["test"]["F1"], 4),
                    "holdout_precision": round(res["test"]["Precision"], 4), "holdout_recall": round(res["test"]["Recall"], 4),
                    "runtime_sec": round(res["runtime"], 1), "comments": comments})
    return res


def annotate(config_id, text):
    if config_id in CONFIG_ROWS:
        row = LOG[CONFIG_ROWS[config_id]]
        row["comments"] = (row["comments"] + " | " if row["comments"] else "") + text


def log_df():
    return pd.DataFrame(LOG)

# %% 5. FeatureBot loop: context, propose, implement, evaluate, select
def paired_delta(res, ref):
    da, df1 = res["cv_auc"] - ref["cv_auc"], res["cv_f1"] - ref["cv_f1"]
    dz = lambda d: float(d.mean() / d.std(ddof=1)) if d.std(ddof=1) > 0 else 0.0
    return {"d_auc": float(da.mean()), "d_f1": float(df1.mean()), "auc_folds_pos": int((da > 0).sum()), "f1_folds_pos": int((df1 > 0).sum()),
            "auc_effect_size": dz(da), "f1_effect_size": dz(df1)}


def passes_rule(d):
    return (d["d_auc"] >= KEEP_MIN_DAUC and d["auc_folds_pos"] >= KEEP_MIN_FOLDS) or (d["d_f1"] >= KEEP_MIN_DF1 and d["f1_folds_pos"] >= KEEP_MIN_FOLDS)


def gender_tpr_gap(res):
    """|TPR_male - TPR_female| on the validation set at the model's own validation threshold."""
    pred = (res["p_val"] >= res["threshold"]).astype(int); y = DATA["y_val"].values; g = DATA["X_val"]["gender"].values
    tprs = [pred[(g == v) & (y == 1)].mean() for v in np.unique(g)]
    return float(max(tprs) - min(tprs))


def run_cycle(cycle, keys, current):
    """Screen each proposal standalone vs baseline, then stepwise addition vs the current accepted set (CV stability)."""
    base = evaluate_config("C0-BASE-LR", (), "lr")
    screen = {}
    for i, k in enumerate(keys, 1):
        r = evaluate_config(f"C{cycle}-S{i:02d}-{k}", {k}, "lr", comments=f"standalone screen of {k} vs baseline")
        screen[k] = paired_delta(r, base)
    order = sorted(keys, key=lambda k: -screen[k]["d_auc"])
    current = set(current); rows, decisions = [], {}
    for k in keys:
        rows.append({"cycle": cycle, "step": "screen (vs baseline)", "feature": k, "reference": "baseline", **{a: round(b, 5) for a, b in screen[k].items()}, "decision": "", "reason": ""})
    for j, k in enumerate(order, 1):
        ref = evaluate_config(f"C{cycle}-REF{j:02d}", current, "lr", log=False) if current else base
        cand = evaluate_config(f"C{cycle}-W{j:02d}-add-{k}", current | {k}, "lr", comments=f"stepwise: add {k} to {len(current)} accepted feature(s)")
        d = paired_delta(cand, ref); ok = passes_rule(d); reason = ""
        if ok:
            reason = (f"stable gain: dAUC {d['d_auc']:+.4f} ({d['auc_folds_pos']}/5 folds +), dF1 {d['d_f1']:+.4f} ({d['f1_folds_pos']}/5 folds +)")
        else:
            reason = (f"low impact / unstable: dAUC {d['d_auc']:+.4f} ({d['auc_folds_pos']}/5 folds +), dF1 {d['d_f1']:+.4f} ({d['f1_folds_pos']}/5 folds +) below keep rule")
        if ok and k in FAIRNESS_AUDITED:
            gap_before, gap_after = gender_tpr_gap(ref), gender_tpr_gap(cand)
            if gap_after - gap_before > FAIRNESS_TPR_GAP_TOL:
                ok = False; reason = f"fairness risk: gender TPR gap widens {gap_before:.3f} -> {gap_after:.3f} (> {FAIRNESS_TPR_GAP_TOL} tolerance) although dAUC {d['d_auc']:+.4f}"
            else:
                reason += f"; fairness audit passed (gender TPR gap {gap_before:.3f} -> {gap_after:.3f})"
        elif k in FAIRNESS_AUDITED:
            reason += f"; gender TPR gap {gender_tpr_gap(ref):.3f} -> {gender_tpr_gap(cand):.3f}"
        if ok:
            current.add(k)
        decisions[k] = {"kept": ok, "reason": reason, "marginal": d}
        rows.append({"cycle": cycle, "step": f"stepwise #{j} (vs accepted set)", "feature": k, "reference": f"{len(current) - (1 if ok else 0)} accepted", **{a: round(b, 5) for a, b in d.items()},
                     "decision": "KEEP" if ok else "REJECT", "reason": reason})
        annotate(f"C{cycle}-W{j:02d}-add-{k}", ("KEPT" if ok else "REJECTED") + ": " + reason)
    end = evaluate_config(f"C{cycle}-END", current, "lr", comments=f"end of cycle {cycle}: accepted set of {len(current)} feature(s)")
    return {"kept": current, "screen": screen, "decisions": decisions, "table": pd.DataFrame(rows), "end": end}


def build_registry(cycles):
    rows = []
    for c in cycles:
        for k, d in c["screen"].items():
            s = SPEC_BY_KEY[k]; dec = c["decisions"][k]
            rows.append({"name": k, "definition": s["definition"], "type": s["type"], "dependencies": s["dependencies"], "leakage_risk": s["leakage_risk"],
                         "added_in_cycle": s["cycle"], "delta_auc": round(d["d_auc"], 4), "delta_f1": round(d["d_f1"], 4),
                         "notes": ("KEPT. " if dec["kept"] else "REJECTED. ") + dec["reason"] + f". delta_* = standalone CV change vs baseline (mean of {N_FOLDS} folds, F1 at 0.5)."})
    return pd.DataFrame(rows)


def context_text(eda, base, errors, extra=""):
    schema = ", ".join(f"{r.column}({r.dtype}, {r.n_unique} unique)" for r in eda.itertuples() if r.column != "income")
    miss = ", ".join(f"{r.column} {r.pct_missing}%" for r in eda.itertuples() if r.n_missing > 0)
    skew = ", ".join(f"{r.column} {r.skew}" for r in eda.itertuples() if r.dtype == "numeric" and abs(r.skew) > 1)
    bal = DATA["y_train"].mean()
    m = base["val"]
    return (f"SCHEMA: {schema}\nTARGET: income (1 = >50K, 0 = <=50K); >50K share in train = {bal:.1%}\nMISSING ('?' -> NaN): {miss}\nSKEWED NUMERICS (|skew|>1): {skew}\n"
            f"BASELINE (Logistic Regression L2, OHE + scaling) VALIDATION: AUC {m['AUC']:.3f}, F1 {m['F1']:.3f} at threshold {m['threshold']:.2f}, precision {m['Precision']:.3f}, recall {m['Recall']:.3f}\n"
            f"TOP ERRORS:\n{errors}\n{extra}")


def error_summary(res, top=5):
    """Validation errors of a fitted config (false negatives are >50K earners that the model misses)."""
    X, y = DATA["X_val"].copy(), DATA["y_val"].values; pred = (res["p_val"] >= res["threshold"]).astype(int)
    X["fn"] = ((pred == 0) & (y == 1)).astype(int); X["pos"] = (y == 1).astype(int)
    m = res["val"]; lines = [f"confusion counts: TP {m['TP']}, FP {m['FP']}, FN {m['FN']}, TN {m['TN']}; miss rate on >50K (FN / positives) = {m['FN'] / max(m['FN'] + m['TP'], 1):.1%}"]
    X["hours_bin"] = pd.cut(X["hours_per_week"], [-1, 30, 40, 50, 1000], labels=["<=30", "31-40", "41-50", "51+"]).astype(str)
    X["has_gain"] = (X["capital_gain"] > 0).map({True: "gain>0", False: "gain=0"})
    for col in ["occupation", "marital_status", "hours_bin", "has_gain"]:
        g = X.groupby(col)[["fn", "pos"]].sum(); g["miss_rate"] = g["fn"] / g["pos"].clip(lower=1)
        g = g[g["pos"] >= 30].sort_values("fn", ascending=False).head(top)
        lines.append(f"false negatives by {col}: " + "; ".join(f"{i}: {int(r.fn)} FN of {int(r.pos)} positives ({r.miss_rate:.0%})" for i, r in g.iterrows()))
    return "\n".join(lines)

# %% 6. Evaluation: ablations, model comparison, interpretability
ALL_KEYS = [s["key"] for s in SPECS]


def run_ablations(final_set, cycle1_set):
    """With / without subsets: reference, baseline, + all cycle-2 interactions, all 18 candidates (no pruning), leave-one-feature-out, without bins."""
    final_set = set(final_set)
    full = evaluate_config("FINAL-SET-LR", final_set, "lr")
    rows = [{"ablation": "kept features (reference)", "features": len(final_set), **_abl_row(full, full)}]
    def add(cid, label, keys, note):
        r = evaluate_config(cid, keys, "lr", comments=note)
        rows.append({"ablation": label, "features": len(keys), **_abl_row(r, full)})
    add("C0-BASE-LR", "no engineered features (baseline)", set(), "baseline")
    add("A01-with-all-cycle2", "kept + all five cycle-2 interactions", final_set | set(KEYS_C2), "ablation: add every cycle-2 interaction on top of the kept set")
    add("A02-all-candidates", f"all {len(ALL_KEYS)} candidate features (no pruning)", set(ALL_KEYS), "ablation: no pruning, every proposed feature enabled")
    for i, k in enumerate(sorted(final_set), 3):
        add(f"A{i:02d}-without-{k}", f"without {k}", final_set - {k}, f"ablation: leave-one-feature-out ({k})")
    bins = {k for k in final_set if SPEC_BY_KEY[k]["group"] == "bins"}
    if len(bins) > 1:
        add("A90-without-bins", "without bins (age_bin + hours_bin)", final_set - bins, "ablation: remove the bin group")
    return pd.DataFrame(rows)


def _abl_row(r, ref):
    return {"cv_auc_mean": round(r["cv_auc"].mean(), 4), "cv_auc_std": round(r["cv_auc"].std(), 4), "cv_f1_mean": round(r["cv_f1"].mean(), 4), "cv_f1_std": round(r["cv_f1"].std(), 4),
            "val_auc": round(r["val"]["AUC"], 4), "val_f1": round(r["val"]["F1"], 4), "holdout_auc": round(r["test"]["AUC"], 4), "holdout_f1": round(r["test"]["F1"], 4),
            "delta_cv_auc_vs_final": round(r["cv_auc"].mean() - ref["cv_auc"].mean(), 4), "delta_val_f1_vs_final": round(r["val"]["F1"] - ref["val"]["F1"], 4)}


def compare_models(final_set):
    rows = []
    for m in available_models():
        for label, tg in [("baseline features", ()), ("enhanced features", tuple(final_set))]:
            r = evaluate_config(f"M-{m.upper()}-{'BASE' if not tg else 'ENH'}", tg, m, comments="model comparison")
            rows.append({"model": MODEL_LABEL[m], "feature_set": label, "cv_auc_mean": round(r["cv_auc"].mean(), 4), "cv_f1_mean": round(r["cv_f1"].mean(), 4),
                         "val_auc": round(r["val"]["AUC"], 4), "val_f1": round(r["val"]["F1"], 4), "holdout_auc": round(r["test"]["AUC"], 4), "holdout_f1": round(r["test"]["F1"], 4)})
    return pd.DataFrame(rows)


def importances(lr_res, rec_res):
    """Global importances: LR coefficients (top 15, enhanced LR) and permutation importance of the model of record (validation set, original columns)."""
    pipe = lr_res["pipe"]; names = None
    try:
        names = list(pipe.named_steps["prep"].get_feature_names_out())
    except Exception:
        pass
    coef = pipe.named_steps["clf"].coef_.ravel()
    if names is None or len(names) != len(coef):
        names = [f"f{i}" for i in range(len(coef))]
    coefs = pd.DataFrame({"feature": names, "coefficient": coef, "abs_coefficient": np.abs(coef)}).sort_values("abs_coefficient", ascending=False).head(15).round(4)
    pi = permutation_importance(rec_res["pipe"], DATA["X_val"], DATA["y_val"], scoring="roc_auc", n_repeats=5, random_state=SEED)
    perm = pd.DataFrame({"column": DATA["X_val"].columns, "auc_drop_mean": pi.importances_mean.round(4), "auc_drop_std": pi.importances_std.round(4)}).sort_values("auc_drop_mean", ascending=False)
    return coefs, perm

# %% 7. Fairness diagnostics & mitigation
def subgroup_table(values, y, p, pred, attr, model_name):
    rows = []
    for g in sorted(pd.Series(values).dropna().unique()):
        m = np.asarray(values == g); yt, pp, pr = np.asarray(y)[m], np.asarray(p)[m], np.asarray(pred)[m]
        tp = int(((pr == 1) & (yt == 1)).sum()); fp = int(((pr == 1) & (yt == 0)).sum()); fn = int(((pr == 0) & (yt == 1)).sum()); tn = int(((pr == 0) & (yt == 0)).sum())
        tpr = tp / (tp + fn) if tp + fn else np.nan; fpr = fp / (fp + tn) if fp + tn else np.nan; prec = tp / (tp + fp) if tp + fp else np.nan
        f1 = 2 * prec * tpr / (prec + tpr) if tp and prec == prec and tpr == tpr and (prec + tpr) > 0 else (0.0 if tp + fn else np.nan)
        auc = roc_auc_score(yt, pp) if len(np.unique(yt)) == 2 else np.nan
        rows.append({"model": model_name, "attribute": attr, "group": g, "n": int(m.sum()), "positives": int(yt.sum()), "selection_rate": pr.mean(),
                     "TPR": tpr, "FPR": fpr, "Precision": prec, "Recall": tpr, "F1": f1, "AUC": auc})
    return pd.DataFrame(rows)


def fairness_tables(X, y, p, pred, model_name):
    attrs = [("gender", X["gender"].values), ("race", X["race"].values), ("marital_status", X["marital_status"].values)]
    return pd.concat([subgroup_table(v, y, p, pred, a, model_name) for a, v in attrs], ignore_index=True)


def parity_ratios(sub):
    rows = []
    for (model, attr), g in sub.groupby(["model", "attribute"]):
        g = g[g["n"] >= MIN_GROUP_N]
        for metric in ["selection_rate", "TPR", "FPR"]:
            v = g.dropna(subset=[metric]); 
            if v.empty:
                continue
            lo, hi = v.loc[v[metric].idxmin()], v.loc[v[metric].idxmax()]
            rows.append({"model": model, "attribute": attr, "metric": metric, "lowest_group": lo["group"], "lowest": round(lo[metric], 4), "highest_group": hi["group"],
                         "highest": round(hi[metric], 4), "parity_ratio": round(lo[metric] / hi[metric], 4) if hi[metric] > 0 else np.nan, "gap": round(hi[metric] - lo[metric], 4),
                         "groups_compared": int(len(v)), "note": f"groups with n < {MIN_GROUP_N} excluded"})
    return pd.DataFrame(rows)


def group_thresholds(res, attr="gender"):
    """Mitigation M2: per-group thresholds chosen on VALIDATION so each group's TPR matches the overall validation TPR."""
    X, y, p = DATA["X_val"], DATA["y_val"].values, res["p_val"]
    target = ((p >= res["threshold"]) & (y == 1)).sum() / (y == 1).sum(); thr = {}
    grid = np.unique(np.round(np.quantile(p, np.linspace(0.01, 0.99, 197)), 4))
    for g in X[attr].dropna().unique():
        m = (X[attr] == g).values
        tprs = np.array([((p[m] >= t) & (y[m] == 1)).sum() / max((y[m] == 1).sum(), 1) for t in grid])
        thr[g] = float(grid[int(np.argmin(np.abs(tprs - target)))])
    return thr, float(target)


def predict_with_group_thresholds(X, p, thr, attr="gender"):
    return np.array([int(pp >= thr[g]) for pp, g in zip(p, X[attr].values)])

# %% 8. Final model & holdout report
def final_fit(toggles, model="lr", drop_cols=(), thr=0.5):
    """Train on train+validation, evaluate ONCE on the holdout test with the validation-chosen threshold."""
    Xf = pd.concat([DATA["X_train"], DATA["X_val"]], ignore_index=True); yf = pd.concat([DATA["y_train"], DATA["y_val"]], ignore_index=True)
    pipe = build_pipeline(toggles, model, drop_cols).fit(Xf, yf)
    p = pipe.predict_proba(DATA["X_test"])[:, 1]
    return pipe, p, compute_metrics(DATA["y_test"], p, thr), compute_metrics(DATA["y_test"], p, 0.5)


def final_figures(y, items):
    """items = [(label, probabilities, metrics-dict)] evaluated on the holdout test."""
    colors = ["#E8833A", "#7A5CC0", "#2F6DB5", "#2E9E5B"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for (lab, p, _), c in zip(items, colors):
        fpr, tpr, _t = roc_curve(y, p); axes[0].plot(fpr, tpr, color=c, label=f"{lab} (AUC {roc_auc_score(y, p):.3f})")
        pr, rc, _t = precision_recall_curve(y, p); axes[1].plot(rc, pr, color=c, label=f"{lab} (PR AUC {average_precision_score(y, p):.3f})")
    axes[0].plot([0, 1], [0, 1], "k:", lw=1); axes[0].set_xlabel("False positive rate"); axes[0].set_ylabel("True positive rate"); axes[0].set_title("ROC - holdout test"); axes[0].legend(fontsize=8)
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("Precision-Recall - holdout test"); axes[1].legend(fontsize=8)
    save_fig(fig, "final_roc_pr.png")
    fig, axes = plt.subplots(1, len(items), figsize=(4.4 * len(items), 3.9))
    for a, (lab, _p, m) in zip(np.atleast_1d(axes), items):
        cm = np.array([[m["TN"], m["FP"]], [m["FN"], m["TP"]]]); a.imshow(cm, cmap="Blues")
        for i in range(2):
            for j in range(2):
                a.text(j, i, f"{cm[i, j]}", ha="center", va="center", fontsize=13, color="white" if cm[i, j] > cm.max() / 2 else "black")
        a.set_xticks([0, 1]); a.set_xticklabels(["<=50K", ">50K"]); a.set_yticks([0, 1]); a.set_yticklabels(["<=50K", ">50K"])
        a.set_xlabel("Predicted"); a.set_ylabel("Actual"); a.set_title(f"{lab}\n(threshold {m['threshold']:.2f})", fontsize=9)
    save_fig(fig, "final_confusion_matrices.png")

# %% 9. Run the whole pipeline (stages map to the notebook sections)
def run_pipeline(data_path=DATA_PATH):
    t_start = time.time(); R = {}
    # --- stage 1: setup and data load (clean, validate, stratified 60/20/20 split)
    reset_state(); os.makedirs(FIG_DIR, exist_ok=True)
    df, checklist = load_data(data_path)
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(df)
    checklist = pd.concat([checklist, split_checks()], ignore_index=True)
    save_csv(checklist, "data_quality_checklist.csv")
    show(checklist, "Data quality checklist")
    # --- stage 2: EDA summary (training split only)
    eda = eda_summary(X_train, y_train)
    # --- stage 3: baseline pipeline (Logistic Regression L2, one-hot encoding + scaling)
    base = evaluate_config("C0-BASE-LR", (), "lr", comments="Phase 1 baseline: raw columns, median/most-frequent imputation, OHE + scaling")
    baseline_metrics = pd.DataFrame([{"split": "validation (threshold tuned on validation)", **{k: round(v, 4) for k, v in base["val"].items()}},
                                     {"split": "validation (threshold 0.5)", **{k: round(v, 4) for k, v in base["val_05"].items()}},
                                     {"split": "5-fold CV on train (threshold 0.5)", "AUC": round(base["cv_auc"].mean(), 4), "F1": round(base["cv_f1"].mean(), 4), "PR_AUC": round(base["cv_ap"].mean(), 4)}])
    save_csv(baseline_metrics, "baseline_metrics.csv")
    show(baseline_metrics, "Baseline metrics")
    print(classification_report(y_val, (base["p_val"] >= base["threshold"]).astype(int), target_names=["<=50K", ">50K"]))
    # --- stage 4a: FeatureBot cycle 1 (Template A: context -> propose -> implement -> evaluate -> select)
    errors_a = error_summary(base)
    prompts = {"A-1": build_prompt(TEMPLATE_A, context_text(eda, base, errors_a)),
               "A-2": build_prompt(TEMPLATE_A, context_text(eda, base, errors_a, "HIGH-CARDINALITY / REMAINING IDEAS: occupation (14 levels), native_country (41 levels), education (16 levels), age x education signal not yet captured"))}
    for pid in ["A-1", "A-2"]:
        print(f"\n===== PROMPT {pid} =====\n{prompts[pid]}\n\n===== RESPONSE {pid} (recorded) =====\n{format_response(pid)}")
    cyc1 = run_cycle(1, KEYS_C1, set())
    show(cyc1["table"][cyc1["table"]["step"].str.startswith("stepwise")][["feature", "d_auc", "d_f1", "auc_folds_pos", "f1_folds_pos", "decision", "reason"]], "Cycle 1 - stepwise decisions")
    registry_v1 = build_registry([cyc1]); save_csv(registry_v1, "feature_registry_v1.csv")
    # --- stage 4b: FeatureBot cycle 2 (Template B: reduce false negatives with targeted interactions)
    errors_b = error_summary(cyc1["end"])
    prompts["B-1"] = build_prompt(TEMPLATE_B, errors_b); prompts["B-2"] = build_prompt(TEMPLATE_B, errors_b + "\nALREADY PROPOSED IN B-1: marital_status x relationship, capital_gain>0 x occupation, occupation x hours bin")
    for pid in ["B-1", "B-2"]:
        print(f"\n===== PROMPT {pid} =====\n{prompts[pid]}\n\n===== RESPONSE {pid} (recorded) =====\n{format_response(pid)}")
    cyc2 = run_cycle(2, KEYS_C2, cyc1["kept"])
    show(cyc2["table"][cyc2["table"]["step"].str.startswith("stepwise")][["feature", "d_auc", "d_f1", "auc_folds_pos", "f1_folds_pos", "decision", "reason"]], "Cycle 2 - stepwise decisions")
    final_set = set(cyc2["kept"])
    registry = build_registry([cyc1, cyc2]); save_csv(registry, "feature_registry.csv")
    cycle_table = pd.concat([cyc1["table"], cyc2["table"]], ignore_index=True); save_csv(cycle_table, "cycle_results.csv")
    show(registry, "Feature registry")
    # --- stage 5: evaluation - ablations, model comparison, interpretability
    ablations = run_ablations(final_set, cyc1["kept"]); save_csv(ablations, "ablations.csv"); show(ablations, "Ablations (with / without subsets)")
    enh_lr = evaluate_config("FINAL-SET-LR", final_set, "lr")
    model_cmp = compare_models(final_set); save_csv(model_cmp, "model_comparison.csv"); show(model_cmp, "Model comparison")
    # model of record = enhanced-feature model with the best VALIDATION AUC among the model families (LR, RF, Gradient Boosting, XGBoost / LightGBM if available)
    final_model = max(available_models(), key=lambda m: evaluate_config(f"M-{m.upper()}-ENH", final_set, m)["val"]["AUC"])
    enh = evaluate_config(f"M-{final_model.upper()}-ENH", final_set, final_model)
    print(f"Model of record (best validation AUC with enhanced features): {MODEL_LABEL[final_model]}")
    coefs, perm = importances(enh_lr, enh); save_csv(coefs, "lr_top_coefficients.csv"); save_csv(perm, "permutation_importance.csv")
    show(coefs, "Top LR coefficients"); show(perm, "Permutation importance (validation, AUC drop)")
    # --- stage 6: fairness diagnostics and mitigation (Template C)
    Xv, yv, Xt, yt = DATA["X_val"], DATA["y_val"].values, DATA["X_test"], DATA["y_test"].values
    sub_val = fairness_tables(Xv, yv, enh["p_val"], (enh["p_val"] >= enh["threshold"]).astype(int), "Enhanced (validation)")
    prompts["C"] = build_prompt(TEMPLATE_C, sub_val[["attribute", "group", "n", "TPR", "FPR", "Precision", "AUC"]].round(3).to_string(index=False))
    print(f"\n===== PROMPT C =====\n{prompts['C']}")
    m1_drop = SENSITIVE + DERIVED_SENSITIVE
    m1 = evaluate_config("FR-M1-exclude-sensitive", final_set, final_model, drop_cols=m1_drop, comments="mitigation M1: exclude gender, race, marital_status and the crosses that contain them")
    thr_g, tpr_target = group_thresholds(enh)
    pred_m2_val = predict_with_group_thresholds(Xv, enh["p_val"], thr_g); pred_m2_test = predict_with_group_thresholds(Xt, enh["p_test"], thr_g)
    m2_val, m2_test = compute_metrics(yv, enh["p_val"], 0.5), compute_metrics(yt, enh["p_test"], 0.5)
    for d_, pr_, y_ in [(m2_val, pred_m2_val, yv), (m2_test, pred_m2_test, yt)]:
        pp, rr, ff, _ = precision_recall_fscore_support(y_, pr_, average="binary", zero_division=0); d_.update({"F1": ff, "Precision": pp, "Recall": rr})
    LOG.append({"config_id": "FR-M2-group-thresholds", "features_enabled": features_summary(final_set) + "; per-gender decision thresholds", "model": MODEL_LABEL[final_model],
                "cv_auc_mean": round(enh["cv_auc"].mean(), 4), "cv_auc_std": round(enh["cv_auc"].std(), 4), "cv_f1_mean": round(enh["cv_f1"].mean(), 4), "cv_f1_std": round(enh["cv_f1"].std(), 4),
                "val_auc": round(enh["val"]["AUC"], 4), "val_f1": round(m2_val["F1"], 4), "val_threshold": round(float(np.mean(list(thr_g.values()))), 3),
                "holdout_auc": round(enh["test"]["AUC"], 4), "holdout_f1": round(m2_test["F1"], 4), "holdout_precision": round(m2_test["Precision"], 4), "holdout_recall": round(m2_test["Recall"], 4),
                "runtime_sec": 0.0, "comments": f"mitigation M2: gender-specific thresholds {({k: round(v, 3) for k, v in thr_g.items()})} matching the overall validation TPR {tpr_target:.3f}; same model as the enhanced model of record"})
    base_pred_t = (base["p_test"] >= base["threshold"]).astype(int); enh_pred_t = (enh["p_test"] >= enh["threshold"]).astype(int); m1_pred_t = (m1["p_test"] >= m1["threshold"]).astype(int)
    subgroup = pd.concat([fairness_tables(Xt, yt, base["p_test"], base_pred_t, "Baseline"), fairness_tables(Xt, yt, enh["p_test"], enh_pred_t, "Enhanced (no mitigation)"),
                          fairness_tables(Xt, yt, m1["p_test"], m1_pred_t, "Enhanced + M1 exclude sensitive features"),
                          fairness_tables(Xt, yt, enh["p_test"], pred_m2_test, "Enhanced + M2 gender thresholds")], ignore_index=True)
    parity = parity_ratios(subgroup)
    save_csv(subgroup.round(4), "subgroup_metrics.csv"); save_csv(parity, "parity_ratios.csv")
    show(subgroup.round(3), "Subgroup metrics (holdout test)"); show(parity, "Parity ratios")
    # --- stage 7: final model on train+validation and holdout report
    ADOPT = os.environ.get("FEATUREBOT_ADOPT", "auto")
    val_loss_f1, val_loss_auc = enh["val"]["F1"] - m1["val"]["F1"], enh["val"]["AUC"] - m1["val"]["AUC"]
    adopt_m1 = (val_loss_f1 <= 0.01 and val_loss_auc <= 0.01) if ADOPT == "auto" else ADOPT == "m1"
    final_drop = tuple(m1_drop) if adopt_m1 else ()
    chosen = m1 if adopt_m1 else enh
    pipe_b, p_b, mb, mb05 = final_fit((), "lr", (), base["threshold"])
    pipe_e, p_e, me, me05 = final_fit(final_set, final_model, final_drop, chosen["threshold"])
    pipe_l, p_l, ml, ml05 = final_fit(final_set, "lr", (), enh_lr["threshold"])
    tag = MODEL_LABEL[final_model] + (" - sensitive features excluded (M1)" if adopt_m1 else "")
    final_metrics = pd.DataFrame([{"model": "Baseline: Logistic Regression, raw columns (train+val fit)", **{k: round(v, 4) for k, v in mb.items()}},
                                  {"model": "Enhanced LR: FeatureBot features only (train+val fit)", **{k: round(v, 4) for k, v in ml.items()}},
                                  {"model": f"Enhanced model of record: {tag} (train+val fit)", **{k: round(v, 4) for k, v in me.items()}},
                                  {"model": "Baseline (threshold 0.5)", **{k: round(v, 4) for k, v in mb05.items()}}, {"model": "Enhanced LR (threshold 0.5)", **{k: round(v, 4) for k, v in ml05.items()}},
                                  {"model": "Enhanced model of record (threshold 0.5)", **{k: round(v, 4) for k, v in me05.items()}}])
    save_csv(final_metrics, "final_metrics.csv"); show(final_metrics, "Final holdout metrics")
    print(classification_report(yt, (p_e >= chosen["threshold"]).astype(int), target_names=["<=50K", ">50K"]))
    final_figures(yt, [("Baseline LR", p_b, mb), ("Enhanced LR (features)", p_l, ml), (f"Enhanced {MODEL_LABEL[final_model]}", p_e, me)])
    LOG.append({"config_id": "F-BASE-LR", "features_enabled": "baseline (raw columns only); trained on train+validation", "model": MODEL_LABEL["lr"], "cv_auc_mean": round(base["cv_auc"].mean(), 4), "cv_auc_std": round(base["cv_auc"].std(), 4),
                "cv_f1_mean": round(base["cv_f1"].mean(), 4), "cv_f1_std": round(base["cv_f1"].std(), 4), "val_auc": round(base["val"]["AUC"], 4), "val_f1": round(base["val"]["F1"], 4), "val_threshold": round(base["threshold"], 3),
                "holdout_auc": round(mb["AUC"], 4), "holdout_f1": round(mb["F1"], 4), "holdout_precision": round(mb["Precision"], 4), "holdout_recall": round(mb["Recall"], 4), "runtime_sec": 0.0,
                "comments": "FINAL baseline: refit on train+validation, holdout evaluated once; CV/validation columns come from the train-only fit of the same configuration"})
    LOG.append({"config_id": "F-ENH", "features_enabled": features_summary(final_set) + (f"; dropped columns: {', '.join(final_drop)}" if final_drop else ""), "model": MODEL_LABEL[final_model],
                "cv_auc_mean": round(chosen["cv_auc"].mean(), 4), "cv_auc_std": round(chosen["cv_auc"].std(), 4), "cv_f1_mean": round(chosen["cv_f1"].mean(), 4), "cv_f1_std": round(chosen["cv_f1"].std(), 4),
                "val_auc": round(chosen["val"]["AUC"], 4), "val_f1": round(chosen["val"]["F1"], 4), "val_threshold": round(chosen["threshold"], 3),
                "holdout_auc": round(me["AUC"], 4), "holdout_f1": round(me["F1"], 4), "holdout_precision": round(me["Precision"], 4), "holdout_recall": round(me["Recall"], 4), "runtime_sec": 0.0,
                "comments": "FINAL enhanced: refit on train+validation, holdout evaluated once; " + ("M1 adopted (sensitive features excluded)" if adopt_m1 else "no exclusion adopted") + "; CV/validation columns from the train-only fit of the same configuration"})
    experiments = log_df(); save_csv(experiments, "experiments_log.csv")
    with open(os.path.join(OUT_DIR, "prompts_and_responses.md"), "w") as f:
        f.write("# FeatureBot prompts and recorded responses\n\nResponses are the AI assistant's proposals as recorded in SPECS (featurebot_adult_income.py).\n")
        for pid in ["A-1", "A-2", "B-1", "B-2"]:
            f.write(f"\n## Prompt {pid}\n\n```\n{prompts[pid]}\n```\n\n### Response {pid}\n\n```\n{format_response(pid)}\n```\n")
        f.write(f"\n## Prompt C (fairness)\n\n```\n{prompts['C']}\n```\n")
    R.update(dict(base=base, enh=enh, enh_lr=enh_lr, final_model=final_model, ml=ml, ml05=ml05, m1=m1, final_set=sorted(final_set), cycle1_set=sorted(cyc1["kept"]), registry=registry, final_metrics=final_metrics, adopt_m1=adopt_m1,
                  thr_g=thr_g, tpr_target=tpr_target, m2_val=m2_val, m2_test=m2_test, mb=mb, me=me, mb05=mb05, me05=me05, runtime=time.time() - t_start,
                  val_loss=(val_loss_f1, val_loss_auc), prompts=prompts, models=available_models()))
    print(f"\nDONE in {R['runtime'] / 60:.1f} min. Outputs written to ./{OUT_DIR}")
    return R


if __name__ == "__main__":
    RESULTS = run_pipeline()
