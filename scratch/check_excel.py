import pandas as pd
excel_path = r"d:\Users\juan_\Documents\Juanan\Programación\Carga de temporada intervals.uci\Temporada 26-27.xlsx"
df = pd.read_excel(excel_path, sheet_name='Entrenamientos')
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(df.iloc[135:143])
