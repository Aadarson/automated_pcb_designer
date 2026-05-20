import sqlite3
import json

conn = sqlite3.connect("pcb_automation.db")
cursor = conn.cursor()
cursor.execute("SELECT status, result, errors FROM designs WHERE id = '81fde49a-6262-4cdc-9d6a-fed6a654b284'")
row = cursor.fetchone()
if row:
    print(f"Status: {row[0]}")
    print(f"Errors: {row[2]}")
    if row[1]:
        res = json.loads(row[1])
        print(f"Progress: {res.get('progress', 0)}%")
else:
    print("Job not found in DB.")
conn.close()
