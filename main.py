# main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, Query
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow frontend access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# UTIL
# ---------------------------------------------------------
def validate_date(date_str: str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format (YYYY-MM-DD)"
        )

# ---------------------------------------------------------
# INPUT SCHEMAS
# ---------------------------------------------------------
class PassengerInput(BaseModel):
    name: str
    age: int


class BookingRequest(BaseModel):
    flight_id: int
    seats: int
    passengers: List[PassengerInput]

# ---------------------------------------------------------
# FLIGHT SEARCH + DYNAMIC PRICING
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
            demand_factor=random.uniform(0.8, 1.2),
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
        demand_factor=random.uniform(0.8, 1.2),
    )

    return flight

# ---------------------------------------------------------
# CREATE BOOKING
# ---------------------------------------------------------
@app.post("/bookings")
def create_booking(
    booking_req: BookingRequest,
    db: Session = Depends(get_db),
):
    flight = db.query(Flight).filter(Flight.id == booking_req.flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    if booking_req.seats <= 0:
        raise HTTPException(status_code=400, detail="Seats must be greater than 0")

    if booking_req.seats != len(booking_req.passengers):
        raise HTTPException(
            status_code=400,
            detail="Seats count must match number of passengers",
        )

    if flight.seats_available < booking_req.seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    price = calculate_dynamic_price(
        base_price=flight.base_price,
        seats_total=flight.seats_total,
        seats_available=flight.seats_available,
        departure_time=flight.departure,
        demand_factor=random.uniform(0.8, 1.2),
    )

    total_price = price * booking_req.seats
    pnr = "PNR" + uuid.uuid4().hex[:8].upper()

    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="Demo user not found")

    try:
        # Lock seats
        flight.seats_available -= booking_req.seats

        booking = Booking(
            user_id=user.id,
            flight_id=flight.id,
            booking_reference=pnr,
            seats_booked=booking_req.seats,
            total_price=total_price,
            currency="INR",
            status="CONFIRMED",
        )
        db.add(booking)
        db.flush()  # get booking.id

        for p in booking_req.passengers:
            db.add(
                BookingPassenger(
                    booking_id=booking.id,
                    passenger_name=p.name,
                    passenger_age=p.age,
                )
            )

        db.add(
            Payment(
                booking_id=booking.id,
                amount=total_price,
                currency="INR",
                payment_method="CARD",
                transaction_reference="TXN"
                + uuid.uuid4().hex[:6].upper(),
                status="SUCCESS",
            )
        )

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Booking confirmed",
        "pnr": pnr,
        "flight_id": flight.id,
        "seats_booked": booking_req.seats,
        "total_price": total_price,
        "currency": "INR",
    }

# ---------------------------------------------------------
# CANCEL BOOKING
# ---------------------------------------------------------
@app.post("/bookings/{pnr}/cancel")
def cancel_booking(pnr: str, db: Session = Depends(get_db)):
    booking = (
        db.query(Booking)
        .filter(
            Booking.booking_reference == pnr,
            Booking.status == "CONFIRMED",
        )
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    flight = db.query(Flight).filter(Flight.id == booking.flight_id).first()
    flight.seats_available += booking.seats_booked
    booking.status = "CANCELLED"

    db.commit()

    return {
        "message": "Booking cancelled successfully",
        "pnr": pnr,
    }

# ---------------------------------------------------------
# BOOKING HISTORY
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
            "created_at": b.created_at,
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
# ---------------------------------------------------------
# DOWNLOAD BOOKING RECEIPT (Milestone 4)
# ---------------------------------------------------------
@app.get("/bookings/{pnr}/receipt")
def download_receipt(pnr: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(
        Booking.booking_reference == pnr
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    flight = db.query(Flight).filter(Flight.id == booking.flight_id).first()

    passengers = db.query(BookingPassenger).filter(
        BookingPassenger.booking_id == booking.id
    ).all()

    return {
        "pnr": booking.booking_reference,
        "flight_id": booking.flight_id,
        "seats_booked": booking.seats_booked,
        "total_price": booking.total_price,
        "currency": booking.currency,
        "status": booking.status,
        "departure": flight.departure if flight else None,
        "passengers": [
            {
                "name": p.passenger_name,
                "age": p.passenger_age
            } for p in passengers
        ],
        "created_at": booking.created_at
    }
# ---------------------------------------------------------
# DOWNLOAD RECEIPT AS PDF (Milestone 4)
# ---------------------------------------------------------
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from fastapi.responses import FileResponse
import os

@app.get("/bookings/{pnr}/receipt/pdf")
def download_receipt_pdf(pnr: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(
        Booking.booking_reference == pnr
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    flight = db.query(Flight).filter(Flight.id == booking.flight_id).first()
    passengers = db.query(BookingPassenger).filter(
        BookingPassenger.booking_id == booking.id
    ).all()

    file_path = f"receipt_{pnr}.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Flight Booking Receipt")

    y -= 40
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"PNR: {booking.booking_reference}")
    y -= 20
    c.drawString(50, y, f"Flight ID: {booking.flight_id}")
    y -= 20
    c.drawString(50, y, f"Seats Booked: {booking.seats_booked}")
    y -= 20
    c.drawString(50, y, f"Total Price: ₹ {booking.total_price}")
    y -= 20
    c.drawString(50, y, f"Status: {booking.status}")
    y -= 20
    c.drawString(50, y, f"Departure: {flight.departure if flight else 'N/A'}")

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Passengers:")

    y -= 20
    c.setFont("Helvetica", 11)
    for p in passengers:
        c.drawString(60, y, f"- {p.passenger_name}, Age: {p.passenger_age}")
        y -= 18

    c.showPage()
    c.save()

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=file_path
    )

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
