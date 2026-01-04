import sqlite3

conn = sqlite3.connect("C:\\Users\\anand\\OneDrive\\Desktop\\Blood Donation project\\blood_donation.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(Donor)")
columns = cur.fetchall()
print(columns)
conn.close()
