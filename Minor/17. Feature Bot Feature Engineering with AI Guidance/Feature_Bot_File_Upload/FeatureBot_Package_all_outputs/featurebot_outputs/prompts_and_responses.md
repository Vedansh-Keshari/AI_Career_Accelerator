# FeatureBot prompts and recorded responses

Responses are the AI assistant's proposals as recorded in SPECS (featurebot_adult_income.py).

## Prompt A-1

```
Given schema + EDA 
----- pasted context -----
SCHEMA: age(numeric, 72 unique), workclass(categorical, 8 unique), fnlwgt(numeric, 20164 unique), education(categorical, 16 unique), educational_num(numeric, 16 unique), marital_status(categorical, 7 unique), occupation(categorical, 14 unique), relationship(categorical, 6 unique), race(categorical, 5 unique), gender(categorical, 2 unique), capital_gain(numeric, 120 unique), capital_loss(numeric, 94 unique), hours_per_week(numeric, 93 unique), native_country(categorical, 41 unique)
TARGET: income (1 = >50K, 0 = <=50K); >50K share in train = 23.9%
MISSING ('?' -> NaN): workclass 5.69%, occupation 5.72%, native_country 1.7%
SKEWED NUMERICS (|skew|>1): fnlwgt 1.315, capital_gain 12.533, capital_loss 4.533, income 1.222
BASELINE (Logistic Regression L2, OHE + scaling) VALIDATION: AUC 0.907, F1 0.695 at threshold 0.36, precision 0.662, recall 0.731
TOP ERRORS:
confusion counts: TP 1709, FP 872, FN 628, TN 6559; miss rate on >50K (FN / positives) = 26.9%
false negatives by occupation: Craft-repair: 127 FN of 257 positives (49%); Prof-specialty: 88 FN of 590 positives (15%); Machine-op-inspct: 67 FN of 91 positives (74%); Sales: 65 FN of 289 positives (22%); Transport-moving: 56 FN of 95 positives (59%)
false negatives by marital_status: Married-civ-spouse: 427 FN of 2020 positives (21%); Never-married: 94 FN of 145 positives (65%); Divorced: 71 FN of 123 positives (58%)
false negatives by hours_bin: 31-40: 359 FN of 1103 positives (33%); 41-50: 158 FN of 686 positives (23%); 51+: 79 FN of 454 positives (17%); <=30: 32 FN of 94 positives (34%)
false negatives by has_gain: gain=0: 610 FN of 1852 positives (33%); gain>0: 18 FN of 485 positives (4%)

----- end of pasted context -----
, propose 5 transformations with rationale, leakage risk, and pandas pseudocode; optimize for F1 on >50K.
```

### Response A-1

```
1. capital_gain_gt0  [binary indicator]
   Rationale: Handles sparsity; flags non-zero gains.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['capital_gain_gt0'] = (df['capital_gain'] > 0).astype(int)
2. capital_loss_gt0  [binary indicator]
   Rationale: Same sparsity argument for losses; loss filers differ from non-filers.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['capital_loss_gt0'] = (df['capital_loss'] > 0).astype(int)
3. capital_gain_log  [numeric transform]
   Rationale: Heavily skewed; log1p compresses the 99999 tail for a linear model.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['capital_gain_log'] = np.log1p(df['capital_gain'])
4. capital_loss_log  [numeric transform]
   Rationale: Heavily skewed; log1p compresses the tail.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['capital_loss_log'] = np.log1p(df['capital_loss'])
5. fnlwgt_log  [numeric transform]
   Rationale: Census weight is right-skewed; log1p symmetrises it.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['fnlwgt_log'] = np.log1p(df['fnlwgt'])
6. age_bin  [categorical bin]
   Rationale: Captures nonlinearity for linear models.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['age_bin'] = pd.cut(df['age'], [0,25,35,45,55,200], labels=['<=25','26-35','36-45','46-55','56+'])
7. hours_bin  [categorical bin]
   Rationale: Overtime signal; stronger separation.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['hours_bin'] = pd.cut(df['hours_per_week'], [-1,30,40,50,1000], labels=['<=30','31-40','41-50','51+'])
```

## Prompt A-2

```
Given schema + EDA 
----- pasted context -----
SCHEMA: age(numeric, 72 unique), workclass(categorical, 8 unique), fnlwgt(numeric, 20164 unique), education(categorical, 16 unique), educational_num(numeric, 16 unique), marital_status(categorical, 7 unique), occupation(categorical, 14 unique), relationship(categorical, 6 unique), race(categorical, 5 unique), gender(categorical, 2 unique), capital_gain(numeric, 120 unique), capital_loss(numeric, 94 unique), hours_per_week(numeric, 93 unique), native_country(categorical, 41 unique)
TARGET: income (1 = >50K, 0 = <=50K); >50K share in train = 23.9%
MISSING ('?' -> NaN): workclass 5.69%, occupation 5.72%, native_country 1.7%
SKEWED NUMERICS (|skew|>1): fnlwgt 1.315, capital_gain 12.533, capital_loss 4.533, income 1.222
BASELINE (Logistic Regression L2, OHE + scaling) VALIDATION: AUC 0.907, F1 0.695 at threshold 0.36, precision 0.662, recall 0.731
TOP ERRORS:
confusion counts: TP 1709, FP 872, FN 628, TN 6559; miss rate on >50K (FN / positives) = 26.9%
false negatives by occupation: Craft-repair: 127 FN of 257 positives (49%); Prof-specialty: 88 FN of 590 positives (15%); Machine-op-inspct: 67 FN of 91 positives (74%); Sales: 65 FN of 289 positives (22%); Transport-moving: 56 FN of 95 positives (59%)
false negatives by marital_status: Married-civ-spouse: 427 FN of 2020 positives (21%); Never-married: 94 FN of 145 positives (65%); Divorced: 71 FN of 123 positives (58%)
false negatives by hours_bin: 31-40: 359 FN of 1103 positives (33%); 41-50: 158 FN of 686 positives (23%); 51+: 79 FN of 454 positives (17%); <=30: 32 FN of 94 positives (34%)
false negatives by has_gain: gain=0: 610 FN of 1852 positives (33%); gain>0: 18 FN of 485 positives (4%)
HIGH-CARDINALITY / REMAINING IDEAS: occupation (14 levels), native_country (41 levels), education (16 levels), age x education signal not yet captured
----- end of pasted context -----
, propose 5 transformations with rationale, leakage risk, and pandas pseudocode; optimize for F1 on >50K.
```

### Response A-2

```
1. overtime  [binary indicator]
   Rationale: Explicit overtime flag (simple, stable).
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['overtime'] = (df['hours_per_week'] > 40).astype(int)
2. age_x_education_num  [numeric interaction]
   Rationale: Seniority / skill proxy.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['age_x_education_num'] = df['age'] * df['educational_num']
3. education_group  [categorical grouping]
   Rationale: Collapses 16 education levels to 4 stable buckets.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['education_group'] = df['education'].map(EDU_GROUP)
4. native_region  [categorical grouping]
   Rationale: 42 sparse countries -> 4 regions; reduces noise.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['native_region'] = df['native_country'].map(REGION).fillna('Other')
5. occupation_catboost  [encoding (target, ordered)]
   Rationale: Medium-cardinality column; one number instead of 15 dummies.
   Leakage risk: Medium by nature (uses target) - mitigated: ordered statistics, fitted inside each CV fold's training rows only
   Pandas pseudocode: enc = ce.CatBoostEncoder(cols=['occupation']); X_tr['occupation_te'] = enc.fit_transform(X_tr, y_tr)['occupation']; X_va = enc.transform(X_va)
6. native_country_freq  [encoding (frequency)]
   Rationale: High-cardinality column; frequency separates the dominant country from rare ones.
   Leakage risk: Low - target never used; counts fitted on train rows only
   Pandas pseudocode: enc = ce.CountEncoder(cols=['native_country'], normalize=True); enc.fit(X_tr)
```

## Prompt B-1

```
Given validation errors 
----- pasted context -----
confusion counts: TP 1791, FP 948, FN 546, TN 6483; miss rate on >50K (FN / positives) = 23.4%
false negatives by occupation: Craft-repair: 93 FN of 257 positives (36%); Prof-specialty: 62 FN of 590 positives (11%); Machine-op-inspct: 61 FN of 91 positives (67%); Sales: 59 FN of 289 positives (20%); Transport-moving: 49 FN of 95 positives (52%)
false negatives by marital_status: Married-civ-spouse: 360 FN of 2020 positives (18%); Never-married: 86 FN of 145 positives (59%); Divorced: 67 FN of 123 positives (54%)
false negatives by hours_bin: 31-40: 306 FN of 1103 positives (28%); 41-50: 103 FN of 686 positives (15%); 51+: 95 FN of 454 positives (21%); <=30: 42 FN of 94 positives (45%)
false negatives by has_gain: gain=0: 521 FN of 1852 positives (28%); gain>0: 25 FN of 485 positives (5%)
----- end of pasted context -----
, suggest 3 interactions to reduce false negatives; provide code and fairness notes.
```

### Response B-1

```
1. marital_x_relationship  [categorical interaction]
   Rationale: Married-civ-spouse heads of household are the largest group of missed >50K earners.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['marital_x_relationship'] = df['marital_status'] + '_x_' + df['relationship']
   Fairness note: marital_status is a sensitive attribute - the cross inherits it; audit TPR gap by marital_status.
2. gain_gt0_x_occupation  [categorical interaction]
   Rationale: A capital gain means something different in Exec-managerial than in Other-service.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['gain_gt0_x_occupation'] = (df['capital_gain']>0).astype(str) + '_x_' + df['occupation'].fillna('Unknown')
   Fairness note: occupation correlates with gender; low direct risk, audit gender TPR gap.
3. occupation_x_hours_bin  [categorical interaction]
   Rationale: Long hours pay off differently by occupation.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['occupation_x_hours_bin'] = df['occupation'].fillna('Unknown') + '_x_' + hours_bin
   Fairness note: Low risk; audit gender TPR gap.
```

## Prompt B-2

```
Given validation errors 
----- pasted context -----
confusion counts: TP 1791, FP 948, FN 546, TN 6483; miss rate on >50K (FN / positives) = 23.4%
false negatives by occupation: Craft-repair: 93 FN of 257 positives (36%); Prof-specialty: 62 FN of 590 positives (11%); Machine-op-inspct: 61 FN of 91 positives (67%); Sales: 59 FN of 289 positives (20%); Transport-moving: 49 FN of 95 positives (52%)
false negatives by marital_status: Married-civ-spouse: 360 FN of 2020 positives (18%); Never-married: 86 FN of 145 positives (59%); Divorced: 67 FN of 123 positives (54%)
false negatives by hours_bin: 31-40: 306 FN of 1103 positives (28%); 41-50: 103 FN of 686 positives (15%); 51+: 95 FN of 454 positives (21%); <=30: 42 FN of 94 positives (45%)
false negatives by has_gain: gain=0: 521 FN of 1852 positives (28%); gain>0: 25 FN of 485 positives (5%)
ALREADY PROPOSED IN B-1: marital_status x relationship, capital_gain>0 x occupation, occupation x hours bin
----- end of pasted context -----
, suggest 3 interactions to reduce false negatives; provide code and fairness notes.
```

### Response B-2

```
1. workclass_x_hours_bin  [categorical interaction]
   Rationale: Self-employed long-hours workers differ from salaried ones.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['workclass_x_hours_bin'] = df['workclass'].fillna('Unknown') + '_x_' + hours_bin
   Fairness note: Low risk.
2. gender_x_occupation  [categorical interaction]
   Rationale: Occupational pay structure may differ by gender.
   Leakage risk: None - row-wise function of raw columns, target never used
   Pandas pseudocode: df['gender_x_occupation'] = df['gender'] + '_x_' + df['occupation'].fillna('Unknown')
   Fairness note: Direct sensitive-attribute interaction - HIGHEST fairness risk; audited for the gender TPR gap before it can be kept.
```

## Prompt C (fairness)

```
Given subgroup metrics 
----- pasted context -----
     attribute                 group    n   TPR   FPR  Precision   AUC
        gender                Female 3238 0.680 0.035      0.696 0.943
        gender                  Male 6530 0.771 0.135      0.715 0.913
          race    Amer-Indian-Eskimo   89 0.385 0.013      0.833 0.883
          race    Asian-Pac-Islander  314 0.722 0.152      0.657 0.887
          race                 Black  954 0.723 0.052      0.686 0.950
          race                 Other   89 0.727 0.064      0.615 0.971
          race                 White 8322 0.764 0.101      0.717 0.928
marital_status              Divorced 1325 0.504 0.013      0.795 0.887
marital_status     Married-AF-spouse    8   NaN 0.125      0.000   NaN
marital_status    Married-civ-spouse 4565 0.800 0.265      0.706 0.860
marital_status Married-spouse-absent  126 0.500 0.036      0.636 0.849
marital_status         Never-married 3189 0.510 0.006      0.813 0.947
marital_status             Separated  287 0.375 0.004      0.857 0.925
marital_status               Widowed  268 0.316 0.004      0.857 0.887
----- end of pasted context -----
, propose mitigations with minimal overall F1 loss; include steps.
```
