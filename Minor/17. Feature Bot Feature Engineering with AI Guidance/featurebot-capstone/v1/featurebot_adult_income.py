# featurebot_adult_income.py  -  FeatureBot starter (leakage-safe, reproducible)
import os, time, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score

SEED, DATA_PATH, OUT = 42, 'adult.csv', 'featurebot_outputs'
os.makedirs(OUT, exist_ok=True)

# 1. Load + clean -----------------------------------------------------------
df = pd.read_csv(DATA_PATH)
df.columns = [c.strip().lower().replace('-', '_') for c in df.columns]
df = df.replace('?', np.nan).rename(columns={'educational_num': 'education_num'})
df['income'] = df['income'].astype(str).str.strip().str.rstrip('.').map({'>50K': 1, '<=50K': 0})
y, X = df.pop('income'), df

# 2. Stratified 60/20/20 split, fixed seed ----------------------------------
Xtv, Xte, ytv, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
Xtr, Xva, ytr, yva = train_test_split(Xtv, ytv, test_size=0.25, stratify=ytv, random_state=SEED)


# 3. Feature block with toggles (row-wise only, so nothing can leak) ---------
def add_feature_block(d, cycle1=True, cycle2=True):
    d = d.copy()
    if cycle1:
        d['capital_gain_gt0'] = (d.capital_gain > 0).astype(int)
        d['capital_loss_gt0'] = (d.capital_loss > 0).astype(int)
        d['log_capital_gain'] = np.log1p(d.capital_gain)
        d['log_capital_loss'] = np.log1p(d.capital_loss)
        d['age_bin'] = pd.cut(
            d.age, [0, 25, 35, 45, 55, 200], labels=['<=25', '26-35', '36-45', '46-55', '56+']
        ).astype(str)
        d['hours_bin'] = pd.cut(
            d.hours_per_week, [-1, 30, 40, 50, 200], labels=['<=30', '31-40', '41-50', '51+']
        ).astype(str)
        d['overtime'] = (d.hours_per_week > 40).astype(int)
        d['age_x_education'] = d.age * d.education_num
    if cycle2:
        hi = {
            'Bachelors': 'Bachelors',
            'Masters': 'Advanced',
            'Prof-school': 'Advanced',
            'Doctorate': 'Advanced',
            'Some-college': 'Some-College',
            'Assoc-voc': 'Some-College',
            'Assoc-acdm': 'Some-College',
        }
        d['education_bucket'] = d.education.map(hi).fillna('HS-or-less')
        amer = [
            'United-States',
            'Mexico',
            'Canada',
            'Puerto-Rico',
            'Cuba',
            'Jamaica',
            'Dominican-Republic',
            'Guatemala',
            'Columbia',
            'El-Salvador',
            'Haiti',
            'Honduras',
            'Ecuador',
            'Peru',
            'Nicaragua',
            'Trinadad&Tobago',
            'Outlying-US(Guam-USVI-etc)',
        ]
        eur = [
            'England',
            'Germany',
            'Italy',
            'Poland',
            'Portugal',
            'France',
            'Greece',
            'Ireland',
            'Hungary',
            'Scotland',
            'Yugoslavia',
            'Holand-Netherlands',
        ]
        asia = [
            'India',
            'Philippines',
            'China',
            'Vietnam',
            'Japan',
            'Taiwan',
            'Iran',
            'South',
            'Cambodia',
            'Thailand',
            'Laos',
            'Hong',
        ]
        d['region'] = d.native_country.apply(
            lambda v: (
                np.nan
                if pd.isna(v)
                else ('Americas' if v in amer else 'Europe' if v in eur else 'Asia' if v in asia else 'Other')
            )
        )
        d['marital_relationship'] = d.marital_status.astype(str) + '|' + d.relationship.astype(str)
        d['workclass_hoursbin'] = (
            d.workclass.astype(str)
            + '|'
            + pd.cut(d.hours_per_week, [-1, 30, 40, 50, 200], labels=['<=30', '31-40', '41-50', '51+']).astype(str)
        )
        d['gain_x_education'] = (d.capital_gain > 0).astype(int) * d.education_num
    return d


# 4. Pipeline fitted on TRAIN only -------------------------------------------
def make_pipeline(d):
    num = d.select_dtypes('number').columns.tolist()
    cat = [c for c in d.columns if c not in num]
    pre = ColumnTransformer(
        [
            ('num', Pipeline([('imp', SimpleImputer(strategy='median')), ('sc', StandardScaler())]), num),
            (
                'cat',
                Pipeline(
                    [
                        ('imp', SimpleImputer(strategy='most_frequent')),
                        ('ohe', OneHotEncoder(handle_unknown='ignore')),
                    ]
                ),
                cat,
            ),
        ]
    )
    return Pipeline([('prep', pre), ('clf', LogisticRegression(max_iter=2000, random_state=SEED))])


def best_threshold(y_true, p):  # chosen on validation only
    grid = np.linspace(0.05, 0.95, 91)
    return float(grid[int(np.argmax([f1_score(y_true, p >= t) for t in grid]))])


log = []


def run(config_id, c1, c2):
    t0 = time.time()
    tr, va = add_feature_block(Xtr, c1, c2), add_feature_block(Xva, c1, c2)
    m = make_pipeline(tr).fit(tr, ytr)
    p = m.predict_proba(va)[:, 1]
    thr = best_threshold(yva, p)
    row = dict(
        config_id=config_id,
        cycle1=c1,
        cycle2=c2,
        val_auc=round(roc_auc_score(yva, p), 4),
        val_f1=round(f1_score(yva, p >= thr), 4),
        threshold=round(thr, 2),
        runtime_s=round(time.time() - t0, 1),
    )
    log.append(row)
    print(row)
    return row


run('baseline', False, False)
run('cycle1', True, False)
run('cycle1+2', True, True)
pd.DataFrame(log).to_csv(f'{OUT}/experiments_log.csv', index=False)

# 5. Final fit on train+validation, report ONCE on the holdout test ------------
Xf, yf = pd.concat([Xtr, Xva]), pd.concat([ytr, yva])
Xf_e, Xte_e = add_feature_block(Xf), add_feature_block(Xte)
final = make_pipeline(Xf_e).fit(Xf_e, yf)
pt = final.predict_proba(Xte_e)[:, 1]
thr = log[-1]['threshold']
print(f"HOLDOUT  AUC {roc_auc_score(yte, pt):.4f}  F1 {f1_score(yte, pt >= thr):.4f}")
