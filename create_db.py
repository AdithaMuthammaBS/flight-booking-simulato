# create_db.py
from models_all import init_db

if __name__ == "__main__":
    init_db()
    print("All tables created successfully in flights.db")
