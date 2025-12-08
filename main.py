# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import datetime
import random

from models_all import Flight, Airport, get_db
from pricing_engine import calculate_dynamic_price


app = FastAPI(
    title="Flight Booking Simulator - API",
    version="2.0",
    description="Flight Search + Dynamic Pricing Engine (Milestone 2)"
)


# Validate date format
def validate_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD")


# ---------------------------------------------------------
# ⭐ FLIGHT SEARCH + DYNAMIC PRICING (Milestone 2)
# ---------------------------------------------------------
@app.get("/flights")
def search_flights(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    date: Optional[str] = None,
    sort_by: Optional[str] = Query("price", regex="^(price|duration|departure)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    query = db.query(Flight)

    # Filter by origin
    if origin:
        airport = db.query(Airport).filter(Airport.code == origin).first()
        if not airport:
            raise HTTPException(status_code=404, detail="Origin not found")
        query = query.filter(Flight.origin_airport_id == airport.id)

    # Filter by destination
    if destination:
        airport = db.query(Airport).filter(Airport.code == destination).first()
        if not airport:
            raise HTTPException(status_code=404, detail="Destination not found")
        query = query.filter(Flight.destination_airport_id == airport.id)

    # Filter by date
    if date:
        filter_date = validate_date(date)
        query = query.filter(
            Flight.departure >= datetime.datetime.combine(filter_date, datetime.time.min),
            Flight.departure <= datetime.datetime.combine(filter_date, datetime.time.max),
        )

    flights = query.all()

    # ---------------------------------------------------------
    # ⭐ APPLY DYNAMIC PRICING (Milestone 2 core logic)
    # ---------------------------------------------------------
    for f in flights:
        f.dynamic_price = calculate_dynamic_price(
            base_price=f.base_price,
            seats_total=f.seats_total,
            seats_available=f.seats_available,
            departure_time=f.departure,
            demand_factor=random.uniform(0.8, 1.2)  # simulated demand
        )

    # ---------------------------------------------------------
    # ⭐ SORTING
    # ---------------------------------------------------------
    if sort_by == "price":
        flights.sort(key=lambda x: x.dynamic_price)
    elif sort_by == "duration":
        flights.sort(key=lambda x: x.duration_minutes)
    elif sort_by == "departure":
        flights.sort(key=lambda x: x.departure)

    if order == "desc":
        flights.reverse()

    return flights


# ---------------------------------------------------------
# ⭐ GET FLIGHT BY ID
# ---------------------------------------------------------
@app.get("/flights/{flight_id}")
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight Not Found")

    # Add dynamic pricing to single flight view
    flight.dynamic_price = calculate_dynamic_price(
        base_price=flight.base_price,
        seats_total=flight.seats_total,
        seats_available=flight.seats_available,
        departure_time=flight.departure,
        demand_factor=random.uniform(0.8, 1.2)
    )

    return flight


# ---------------------------------------------------------
# ⭐ EXTERNAL AIRLINE FEED SIMULATION
# ---------------------------------------------------------
@app.get("/external/airline_feed")
def airline_feed():
    example = []
    for _ in range(5):
        example.append({
            "flight_number": "EXT" + str(random.randint(100, 999)),
            "origin": random.choice(["BLR", "DEL", "HYD", "COK"]),
            "destination": random.choice(["BLR", "DEL", "HYD", "COK"]),
            "price": random.randint(3000, 10000),
            "duration": random.randint(60, 180),
        })
    return JSONResponse(content=example)
