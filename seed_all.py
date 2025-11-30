# seed_all.py
from models_all import SessionLocal, init_db, Airline, Airport, Flight, User, Booking, BookingPassenger, FareHistory, Payment
import datetime, random, uuid

# ensure tables exist
init_db()

db = SessionLocal()

# --- Insert airlines (idempotent)
airlines = ["AirBlue","IndiSky","Nimbus","JetRapid"]
airline_objs = []
for name in airlines:
    existing = db.query(Airline).filter(Airline.name == name).first()
    if existing:
        airline_objs.append(existing)
    else:
        a = Airline(name=name, code=name[:2].upper())
        db.add(a)
        db.flush()   # get id without committing
        airline_objs.append(a)
db.commit()

# --- Insert airports (idempotent)
ap_data = [
    ("BLR", "Bengaluru Intl", "Bengaluru", "India"),
    ("DEL", "Indira Gandhi Intl", "Delhi", "India"),
    ("MAA", "Chennai Intl", "Chennai", "India"),
    ("BOM", "Chhatrapati Shivaji", "Mumbai", "India"),
    ("HYD", "Rajiv Gandhi Intl", "Hyderabad", "India")
]
airport_objs = []
for iata, name, city, country in ap_data:
    existing = db.query(Airport).filter(Airport.iata == iata).first()
    if existing:
        airport_objs.append(existing)
    else:
        ap = Airport(iata=iata, name=name, city=city, country=country)
        db.add(ap)
        db.flush()
        airport_objs.append(ap)
db.commit()


# mapping for ids
iata_map = {a.iata: a.id for a in db.query(Airport).all()}
airline_map = {a.name: a.id for a in db.query(Airline).all()}

# --- Insert flights (20 sample flights)
for i in range(20):
    origin, dest = random.sample(list(iata_map.keys()), 2)
    dep_date = datetime.datetime.now() + datetime.timedelta(days=random.randint(0,14))
    dep = dep_date.replace(hour=random.randint(5,22), minute=random.choice([0,15,30,45]), second=0)
    duration = random.randint(60, 300)
    arr = dep + datetime.timedelta(minutes=duration)
    airline = random.choice(list(airline_map.keys()))
    f = Flight(
        airline_id=airline_map[airline],
        flight_number=f"{airline[:2].upper()}{random.randint(100,999)}",
        origin_airport_id=iata_map[origin],
        destination_airport_id=iata_map[dest],
        departure=dep,
        arrival=arr,
        duration_minutes=duration,
        seats_total=180,
        seats_available=random.randint(10,180),
        base_price=round(random.uniform(2000,15000), 2),
        currency="INR",
        refundable=random.choice([True, False])
    )
    db.add(f)
db.commit()

# --- Create a demo user
user = User(email="demo@example.com", full_name="Demo User", phone="9999999999")
db.add(user)
db.commit()

# --- Create a demo booking for first flight
first_flight = db.query(Flight).first()
if first_flight:
    booking_ref = "BR" + uuid.uuid4().hex[:8].upper()
    seats = 2
    price_total = first_flight.base_price * seats
    booking = Booking(
        user_id=user.id,
        flight_id=first_flight.id,
        booking_reference=booking_ref,
        seats_booked=seats,
        total_price=price_total,
        currency="INR",
        status="CONFIRMED"
    )
    db.add(booking)
    db.commit()

    # passengers
    p1 = BookingPassenger(booking_id=booking.id, passenger_name="Alice Demo", passenger_age=28)
    p2 = BookingPassenger(booking_id=booking.id, passenger_name="Bob Demo", passenger_age=30)
    db.add_all([p1, p2])

    # payment
    pay = Payment(
        booking_id=booking.id,
        amount=price_total,
        currency="INR",
        payment_method="CARD",
        transaction_reference="TXN" + uuid.uuid4().hex[:6].upper(),
        status="SUCCESS"
    )
    db.add(pay)

    # fare history
    fh = FareHistory(flight_id=first_flight.id, price=first_flight.base_price, reason="initial")
    db.add(fh)

    db.commit()

print("Seeding complete!")
db.close()
