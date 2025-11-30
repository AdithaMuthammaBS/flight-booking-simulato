# pricing_engine.py
from datetime import datetime

def calculate_dynamic_price(base_price, seats_total, seats_available, departure_time, demand_factor=1.0):

    # 1️⃣ Seat availability factor
    seats_used = seats_total - seats_available
    seat_fill_percentage = seats_used / seats_total  # value between 0 and 1

    seat_price_factor = 1 + (seat_fill_percentage * 0.5)  
    # Example: if 60% seats filled → +30% price

    # 2️⃣ Time until departure factor
    hours_to_departure = (departure_time - datetime.now()).total_seconds() / 3600

    if hours_to_departure < 0:
        time_factor = 1
    elif hours_to_departure < 24:
        time_factor = 1.4
    elif hours_to_departure < 72:
        time_factor = 1.2
    else:
        time_factor = 1.0

    # 3️⃣ Simulated demand factor (1.0 = normal, >1 = high demand)
    demand_factor = demand_factor  

    # 4️⃣ Final dynamic price calculation
    final_price = base_price * seat_price_factor * time_factor * demand_factor

    return round(final_price, 2)
