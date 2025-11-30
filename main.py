# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import datetime

from models_all import SessionLocal, init_db, Flight, Airline, Airport
from fastapi.responses import JSONResponse

app = FastAPI(title="Flight Booking Simulator - API")

# Initialize database tables
init_db()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------
# GET /flights  — Search flights
# ---------------------------------------------------
@app.get("/flights")
def search_flights(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    date: Optional[str] = None,
    sort_by: str = Query("price", regex="^(price|duration|departure)$"),
    order: str = Query("asc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):

    query = db.query(Flight)

    if origin:
        origin_airport = db.query(Airport).filter(Airport.iata == origin.upper()).first()
        if origin_airport:
            query = query.filter(Flight.origin_airport_id == origin_airport.id)

    if destination:
        dest_airport = db.query(Airport).filter(Airport.iata == destination.upper()).first()
        if dest_airport:
            query = query.filter(Flight.destination_airport_id == dest_airport.id)

    if date:
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            start = datetime.datetime.combine(date_obj, datetime.time.min)
            end = datetime.datetime.combine(date_obj, datetime.time.max)
            query = query.filter(Flight.departure >= start, Flight.departure <= end)
        except:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Sorting logic
    if sort_by == "price":
        order_clause = Flight.base_price.asc() if order == "asc" else Flight.base_price.desc()
    elif sort_by == "duration":
        order_clause = Flight.duration_minutes.asc() if order == "asc" else Flight.duration_minutes.desc()
    else:
        order_clause = Flight.departure.asc() if order == "asc" else Flight.departure.desc()

    flights = query.order_by(order_clause).all()

    return flights


# ---------------------------------------------------
# GET /flights/{id} — Flight details
# ---------------------------------------------------
@app.get("/flights/{flight_id}")
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


# ---------------------------------------------------
# GET /external/airline_feed  — Simulated external API
# ---------------------------------------------------
@app.get("/external/airline_feed")
def external_airline_feed(date: Optional[str] = None):
    import random
    base_date = datetime.date.today()

    if date:
        try:
            base_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except:
            raise HTTPException(status_code=400, detail="Use date format YYYY-MM-DD")

    sample_airlines = ["AirBlue", "IndiSky", "Nimbus", "JetRapid"]
    sample_routes = [("BLR", "DEL"), ("DEL", "BOM"), ("MAA", "BLR"), ("HYD", "CCU")]

    flights = []
    for i in range(10):
        airline = random.choice(sample_airlines)
        origin, dest = random.choice(sample_routes)

        dep_time = datetime.datetime.combine(base_date, datetime.time(hour=random.randint(5, 22)))
        duration = random.randint(60, 300)
        arr_time = dep_time + datetime.timedelta(minutes=duration)

        flights.append({
            "airline": airline,
            "flight_number": f"{airline[:2].upper()}{random.randint(100,999)}",
            "origin": origin,
            "destination": dest,
            "departure": dep_time.isoformat(),
            "arrival": arr_time.isoformat(),
            "price": round(random.uniform(2000, 10000), 2)
        })

    return JSONResponse(content={"date": base_date.isoformat(), "flights": flights})
