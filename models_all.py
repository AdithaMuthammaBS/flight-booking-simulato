# models_all.py
import datetime
import os
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

# -------------------------
# MODELS
# -------------------------

class Airline(Base):
    __tablename__ = "airlines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    code = Column(String(10))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    flights = relationship("Flight", back_populates="airline", cascade="all, delete-orphan")


class Airport(Base):
    __tablename__ = "airports"
    id = Column(Integer, primary_key=True, index=True)
    iata = Column(String(8), unique=True, nullable=False)
    name = Column(String(128))
    city = Column(String(64))
    country = Column(String(64))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True)
    airline_id = Column(Integer, ForeignKey("airlines.id"), nullable=False)
    flight_number = Column(String(32), nullable=False)
    origin_airport_id = Column(Integer, ForeignKey("airports.id"), nullable=False)
    destination_airport_id = Column(Integer, ForeignKey("airports.id"), nullable=False)
    departure = Column(DateTime, nullable=False)
    arrival = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    seats_total = Column(Integer, nullable=False, default=180)
    seats_available = Column(Integer, nullable=False, default=180)
    base_price = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    refundable = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    airline = relationship("Airline", back_populates="flights")
    origin_airport = relationship("Airport", foreign_keys=[origin_airport_id])
    destination_airport = relationship("Airport", foreign_keys=[destination_airport_id])
    bookings = relationship("Booking", back_populates="flight", cascade="all, delete-orphan")
    fare_history = relationship("FareHistory", back_populates="flight", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(128), nullable=False, unique=True)
    full_name = Column(String(128))
    phone = Column(String(32))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    booking_reference = Column(String(64), nullable=False, unique=True)
    seats_booked = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    status = Column(String(32), default="CONFIRMED")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")
    passengers = relationship("BookingPassenger", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")


class BookingPassenger(Base):
    __tablename__ = "booking_passengers"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    passenger_name = Column(String(128), nullable=False)
    passenger_age = Column(Integer)
    passenger_type = Column(String(8), default="ADT")
    seat_number = Column(String(16))

    booking = relationship("Booking", back_populates="passengers")


class FareHistory(Base):
    __tablename__ = "fare_history"
    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)
    price = Column(Float, nullable=False)
    reason = Column(Text)

    flight = relationship("Flight", back_populates="fare_history")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    paid_at = Column(DateTime, default=datetime.datetime.utcnow)
    payment_method = Column(String(32))
    transaction_reference = Column(String(128))
    status = Column(String(32), default="SUCCESS")

    booking = relationship("Booking", back_populates="payments")


# -------------------------
# DATABASE SETUP
# -------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./flights.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)


# -------------------------
# FASTAPI DEPENDENCY
# -------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
