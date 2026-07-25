import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    dbname="hengineers_db",
    user="postgres",
    password="Netfiber2026",  # <-- type your ACTUAL new password here, exactly
)
print("Connected successfully!")
conn.close()