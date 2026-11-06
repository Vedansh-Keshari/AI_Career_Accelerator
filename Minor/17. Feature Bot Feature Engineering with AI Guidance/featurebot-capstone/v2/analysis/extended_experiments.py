"""Extended experiments: logistic regression vs gradient boosting, with 5-fold CV (run from the repo root).
Writes results/extended_experiments.csv. Needs adult.csv (see prepare_data.py)."""
import os, numpy as np, pandas as pd, json, time, warnings
warnings.filterwarnings('ignore')
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix, average_precision_score, brier_score_loss, roc_curve, precision_recall_curve
SEED=42
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df=pd.read_csv(os.path.join(ROOT,'adult.csv'))
df.columns=[c.strip().lower().replace('-','_') for c in df.columns]
df=df.replace('?',np.nan)
df['income']=df['income'].astype(str).str.strip().str.rstrip('.').map({'>50K':1,'<=50K':0})
df=df.rename(columns={'educational_num':'education_num'})
y=df.pop('income'); X=df
Xtv,Xte,ytv,yte=train_test_split(X,y,test_size=.2,stratify=y,random_state=SEED)
Xtr,Xva,ytr,yva=train_test_split(Xtv,ytv,test_size=.25,stratify=ytv,random_state=SEED)
print(len(Xtr),len(Xva),len(Xte))

def add(df,flags):
    d=df.copy()
    if 'c1' in flags:
        d['capital_gain_gt0']=(d.capital_gain>0).astype(int)
        d['capital_loss_gt0']=(d.capital_loss>0).astype(int)
        d['log_capital_gain']=np.log1p(d.capital_gain); d['log_capital_loss']=np.log1p(d.capital_loss)
        d['age_bin']=pd.cut(d.age,[0,25,35,45,55,200],labels=['<=25','26-35','36-45','46-55','56+']).astype(str)
        d['hours_bin']=pd.cut(d.hours_per_week,[-1,30,40,50,200],labels=['<=30','31-40','41-50','51+']).astype(str)
        d['overtime']=(d.hours_per_week>40).astype(int)
        d['age_x_education']=d.age*d.education_num
    if 'c2' in flags:
        m={'Preschool':'HS-or-less','1st-4th':'HS-or-less','5th-6th':'HS-or-less','7th-8th':'HS-or-less','9th':'HS-or-less','10th':'HS-or-less','11th':'HS-or-less','12th':'HS-or-less','HS-grad':'HS-or-less','Some-college':'Some-College','Assoc-voc':'Some-College','Assoc-acdm':'Some-College','Bachelors':'Bachelors','Masters':'Advanced','Prof-school':'Advanced','Doctorate':'Advanced'}
        d['education_bucket']=d.education.map(m)
        amer=['United-States','Mexico','Canada','Puerto-Rico','Cuba','Jamaica','Dominican-Republic','Guatemala','Columbia','El-Salvador','Haiti','Honduras','Ecuador','Peru','Nicaragua','Trinadad&Tobago','Outlying-US(Guam-USVI-etc)']
        eur=['England','Germany','Italy','Poland','Portugal','France','Greece','Ireland','Hungary','Scotland','Yugoslavia','Holand-Netherlands']
        asia=['India','Philippines','China','Vietnam','Japan','Taiwan','Iran','South','Cambodia','Thailand','Laos','Hong','Hong-Kong']
        d['region']=d.native_country.apply(lambda v: np.nan if pd.isna(v) else 'Americas' if v in amer else 'Europe' if v in eur else 'Asia' if v in asia else 'Other')
        d['marital_relationship']=d.marital_status.astype(str)+'|'+d.relationship.astype(str)
        d['workclass_hoursbin']=d.workclass.astype(str)+'|'+pd.cut(d.hours_per_week,[-1,30,40,50,200],labels=['<=30','31-40','41-50','51+']).astype(str)
        d['gain_x_education']=d.capital_gain_gt0*d.education_num if 'capital_gain_gt0' in d else (d.capital_gain>0).astype(int)*d.education_num
    return d

def build(Xs,drop=()):
    Xs=Xs.drop(columns=[c for c in drop if c in Xs.columns])
    num=Xs.select_dtypes(include=['int64','float64','int32']).columns.tolist()
    cat=[c for c in Xs.columns if c not in num]
    pre=ColumnTransformer([('n',Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler())]),num),
        ('c',Pipeline([('i',SimpleImputer(strategy='most_frequent')),('o',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),cat)])
    return pre
def model(Xs,flags,drop=(),kind='lr'):
    pre=build(add(Xs,flags),drop)
    clf=LogisticRegression(max_iter=2000,random_state=SEED,C=1.0) if kind=='lr' else HistGradientBoostingClassifier(random_state=SEED,max_iter=200,learning_rate=.1)
    if kind=='gb':
        pre=ColumnTransformer([('n','passthrough',[]),],remainder='drop') if False else pre
    return Pipeline([('p',pre),('c',clf)])
def best_thr(y,p):
    ts=np.linspace(.05,.95,91); f=[f1_score(y,p>=t) for t in ts]; return float(ts[int(np.argmax(f))])
def evaluate(flags,drop=(),kind='lr',name=''):
    t0=time.time()
    m=model(Xtr,flags,drop,kind).fit(add(Xtr,flags).drop(columns=[c for c in drop if c in add(Xtr,flags).columns]),ytr)
    f=lambda Z: add(Z,flags).drop(columns=[c for c in drop if c in add(Z,flags).columns])
    pv=m.predict_proba(f(Xva))[:,1]; thr=best_thr(yva,pv)
    # CV on train
    skf=StratifiedKFold(5,shuffle=True,random_state=SEED); aucs=[];f1s=[]
    for a,b in skf.split(Xtr,ytr):
        mm=model(Xtr.iloc[a],flags,drop,kind).fit(f(Xtr.iloc[a]),ytr.iloc[a]); pp=mm.predict_proba(f(Xtr.iloc[b]))[:,1]
        aucs.append(roc_auc_score(ytr.iloc[b],pp)); f1s.append(f1_score(ytr.iloc[b],pp>=thr))
    r=dict(name=name,val_auc=roc_auc_score(yva,pv),val_f1=f1_score(yva,pv>=thr),thr=thr,cv_auc=np.mean(aucs),cv_auc_sd=np.std(aucs),cv_f1=np.mean(f1s),cv_f1_sd=np.std(f1s),runtime=time.time()-t0)
    return r,m,f

rows = []
for k, (fl, kind) in {'base_lr': ([], 'lr'), 'c1_lr': (['c1'], 'lr'), 'c2_lr': (['c1', 'c2'], 'lr'),
                      'base_gb': ([], 'gb'), 'c1_gb': (['c1'], 'gb'), 'c2_gb': (['c1', 'c2'], 'gb')}.items():
    r, _, _ = evaluate(fl, kind=kind, name=k)
    rows.append({a: (round(float(v), 4) if not isinstance(v, str) else v) for a, v in r.items()})
    print(rows[-1])
os.makedirs(os.path.join(ROOT, 'results'), exist_ok=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT, 'results', 'extended_experiments.csv'), index=False)
