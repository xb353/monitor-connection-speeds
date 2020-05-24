
import pandas as pd 
import sqlite3

 # Sqlite database path
DB_PATH = 'speeds.db'

# Sqlite table name
DB_TABLE_NAME = "speed"

# Read sqlite query results into a pandas DataFrame
print("+ Connecting to DB...")
con = sqlite3.connect(DB_PATH)
print("+ Querying...")
df = pd.read_sql_query(f"SELECT * from {DB_TABLE_NAME}", con)
print("+ Writing...")
df.to_csv("speeds.csv", index=False)
con.close()
print("- Done!")

