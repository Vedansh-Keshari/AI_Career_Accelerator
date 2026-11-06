"""Convert the course workbook (Resources_Dataset.xlsx) into adult.csv, which the FeatureBot script expects."""
import sys
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else 'Resources_Dataset.xlsx'
df = pd.read_excel(src)
df.to_csv('adult.csv', index=False)
print(f'Wrote adult.csv with {len(df):,} rows and {df.shape[1]} columns')
