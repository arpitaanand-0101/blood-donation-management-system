import streamlit as st
import sqlite3
import pandas as pd

st.title("Blood Donation DB — Table Checker")

# connect to the SQLite database
conn = sqlite3.connect('blooddb.sqlite')
cur = conn.cursor()

# fetch table names
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cur.fetchall()]

st.subheader("Tables in the database:")
st.write(tables)

# dropdown to select a table
table_to_view = st.selectbox("Choose a table to view", tables)

if table_to_view:
    df = pd.read_sql_query(f"SELECT * FROM {table_to_view} LIMIT 10;", conn)
    st.subheader(f"Sample records from {table_to_view}")
    st.dataframe(df)

conn.close()
