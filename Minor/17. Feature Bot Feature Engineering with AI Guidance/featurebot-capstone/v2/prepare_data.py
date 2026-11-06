"""Convert the course workbook (Resources_Dataset.xlsx) into adult.csv, which the FeatureBot script expects."""
import os
import sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'Resources_Dataset.xlsx')
df = pd.read_excel(src)
df.to_csv(os.path.join(HERE, 'adult.csv'), index=False)
print(f'Wrote adult.csv with {len(df):,} rows and {df.shape[1]} columns')
