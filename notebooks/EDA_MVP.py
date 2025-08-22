# Quick EDA example
import pandas as pd
import matplotlib.pyplot as plt
df=pd.read_csv('../data/sample_sales.csv',parse_dates=['date'])
df['ym']=df['date'].dt.to_period('M').dt.to_timestamp()
monthly=df.groupby('ym')['revenue'].sum(); monthly.plot(marker='o'); plt.show()
