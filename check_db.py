import sqlite3

con = sqlite3.connect("flights.db")
cur = con.cursor()

print("TABLES:")
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(tables)

print("\nROW COUNTS:")
for table in ["airlines", "airports", "flights", "users", "bookings", "booking_passengers", "fare_history", "payments"]:
    try:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")
    except Exception as e:
        print(f"{table}: ERROR → {e}")

con.close()
