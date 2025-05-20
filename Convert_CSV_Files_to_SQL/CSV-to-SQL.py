import os
import pandas as pd
import sqlite3

# Paths
root_dir = r'D:\Data_for_query_tool\data'  # Upload this directory here
database_file = 'vehicle_analysis.db'

# Connect to SQLite DB
conn = sqlite3.connect(database_file)
cursor = conn.cursor()

# Cleaning function
def clean_dataframe(df):
    # Drop 'Total' row and column
    df = df[~df.iloc[:, 0].str.lower().str.contains("total", na=False)]  # Remove 'Total' row
    df = df.loc[:, ~df.columns.str.lower().str.contains("total", na=False)]  # Remove 'Total' column
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

# Table-friendly folder name
def sanitize_folder_name(name):
    return name.lower().replace(" ", "_").replace("(", "").replace(")", "")

# Process each folder
for folder in os.listdir(root_dir):
    folder_path = os.path.join(root_dir, folder)
    if not os.path.isdir(folder_path):
        continue
    
    table_name = sanitize_folder_name(folder)

    for file in os.listdir(folder_path):
        if not file.endswith('.csv'):
            continue
        
        year = os.path.splitext(file)[0]  # "2009", "2010", etc.
        file_path = os.path.join(folder_path, file)

        df = pd.read_csv(file_path)
        df = clean_dataframe(df)

        # Melt if needed (from wide to long format)
        df_long = df.melt(id_vars=[df.columns[0]], var_name='column_value', value_name='count')
        df_long.rename(columns={df.columns[0]: 'row_value'}, inplace=True)

        # Add metadata
        df_long['year'] = int(year)
        df_long['source_table'] = table_name

        # Write to SQL
        df_long.to_sql(table_name, conn, if_exists='append', index=False)

# Close DB
conn.commit()
conn.close()

print("✅ All CSV files have been successfully written to the SQLite database.")
