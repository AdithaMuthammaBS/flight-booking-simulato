# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import datetime
import random
import uuid

from models_all import (
    Flight,
    Airport,
    Booking,
    BookingPassenger,
    User,
    Payment,
    get_db,
)
from pricing_engine import calculate_dynamic_price

# ---------------------------------------------------------
# APP CONFIG
# ---------------------------------------------------------
app = FastAPI(
    title="Flight Booking Simulator - API",
    version="3.0",
    description="Flight Search + Dynamic Pricing + Booking Workflow"
)

# ---------------------------------------------------------
# UTIL
# ---------------------------------------------------------
def validate_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")

# ---------------------------------------------------------
# BOOKING INPUT SCHEMAS (Milestone 3)
# ---------------------------------------------------------
class PassengerInput(BaseModel):
    name: str
    age: int


class BookingRequest(BaseModel):
    flight_id: int
    seats: int
    passengers: List[PassengerInput]

# ---------------------------------------------------------
# FLIGHT SEARCH + DYNAMIC PRICING (Milestone 2)
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

    if origin:
        airport = db.query(Airport).filter(Airport.iata == origin).first()
        if not airport:
            raise HTTPException(status_code=404, detail="Origin not found")
        query = query.filter(Flight.origin_airport_id == airport.id)

    if destination:
        airport = db.query(Airport).filter(Airport.iata == destination).first()
        if not airport:
            raise HTTPException(status_code=404, detail="Destination not found")
        query = query.filter(Flight.destination_airport_id == airport.id)

    if date:
        d = validate_date(date)
        query = query.filter(
            Flight.departure >= datetime.datetime.combine(d, datetime.time.min),
            Flight.departure <= datetime.datetime.combine(d, datetime.time.max),
        )

    flights = query.all()

    for f in flights:
        f.dynamic_price = calculate_dynamic_price(
            base_price=f.base_price,
            seats_total=f.seats_total,
            seats_available=f.seats_available,
            departure_time=f.departure,
            demand_factor=random.uniform(0.8, 1.2)
        )

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
# GET FLIGHT BY ID
# ---------------------------------------------------------
@app.get("/flights/{flight_id}")
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    flight.dynamic_price = calculate_dynamic_price(
        base_price=flight.base_price,
        seats_total=flight.seats_total,
        seats_available=flight.seats_available,
        departure_time=flight.departure,
        demand_factor=random.uniform(0.8, 1.2)
    )
    return flight

# ---------------------------------------------------------
# CREATE BOOKING (Milestone 3)
# ---------------------------------------------------------
@app.post("/bookings")
def create_booking(
    booking_req: BookingRequest,
    db: Session = Depends(get_db)
):
    flight = db.query(Flight).filter(Flight.id == booking_req.flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    if booking_req.seats <= 0:
        raise HTTPException(status_code=400, detail="Seats must be > 0")

    if booking_req.seats != len(booking_req.passengers):
        raise HTTPException(
            status_code=400,
            detail="Seats count must match passengers"
        )

    if flight.seats_available < booking_req.seats:
        raise HTTPException(status_code=400, detail="Not enough seats")

    price = calculate_dynamic_price(
        base_price=flight.base_price,
        seats_total=flight.seats_total,
        seats_available=flight.seats_available,
        departure_time=flight.departure,
        demand_factor=random.uniform(0.8, 1.2)
    )

    total_price = price * booking_req.seats
    pnr = "PNR" + uuid.uuid4().hex[:8].upper()

    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="No demo user found")

    try:
        flight.seats_available -= booking_req.seats

        booking = Booking(
            user_id=user.id,
            flight_id=flight.id,
            booking_reference=pnr,
            seats_booked=booking_req.seats,
            total_price=total_price,
            currency="INR",
            status="CONFIRMED"
        )
        db.add(booking)
        db.flush()

        for p in booking_req.passengers:
            db.add(BookingPassenger(
                booking_id=booking.id,
                passenger_name=p.name,
                passenger_age=p.age
            ))

        db.add(Payment(
            booking_id=booking.id,
            amount=total_price,
            currency="INR",
            payment_method="CARD",
            transaction_reference="TXN" + uuid.uuid4().hex[:6].upper(),
            status="SUCCESS"
        ))

        db.commit()

    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="Booking failed")

        return {
        "message": "Booking confirmed",
        "pnr": pnr,
        "flight_id": flight.id,
        "seats_booked": booking_req.seats,
        "total_price": total_price,
        "currency": "INR"
    }
# ---------------------------------------------------------
# CANCEL BOOKING (Milestone 3)
# ---------------------------------------------------------
@app.post("/bookings/{pnr}/cancel")
def cancel_booking(pnr: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(
        Booking.booking_reference == pnr,
        Booking.status == "CONFIRMED"
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or already cancelled")

    flight = db.query(Flight).filter(Flight.id == booking.flight_id).first()

    flight.seats_available += booking.seats_booked
    booking.status = "CANCELLED"

    db.commit()

    return {
        "message": "Booking cancelled successfully",
        "pnr": pnr,
        "seats_refunded": booking.seats_booked
    }


# ---------------------------------------------------------
# BOOKING HISTORY (Milestone 3)
# ---------------------------------------------------------
@app.get("/bookings/history")
def booking_history(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bookings = db.query(Booking).filter(Booking.user_id == user.id).all()

    return [
        {
            "pnr": b.booking_reference,
            "flight_id": b.flight_id,
            "seats": b.seats_booked,
            "total_price": b.total_price,
            "status": b.status,
            "created_at": b.created_at
        }
        for b in bookings
    ]


# ---------------------------------------------------------
# EXTERNAL AIRLINE FEED
# ---------------------------------------------------------
@app.get("/external/airline_feed")
def airline_feed():
    return [
        {
            "flight_number": "EXT" + str(random.randint(100, 999)),
            "origin": random.choice(["BLR", "DEL", "HYD"]),
            "destination": random.choice(["BLR", "DEL", "HYD"]),
            "price": random.randint(3000, 10000),
            "duration": random.randint(60, 180),
        }
        for _ in range(5)
    ]
