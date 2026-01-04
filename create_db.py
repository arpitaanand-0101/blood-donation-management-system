import sqlite3

# create the SQLite database file
conn = sqlite3.connect('blooddb.sqlite')
conn.close()

print("Database blooddb.sqlite created successfully!")
