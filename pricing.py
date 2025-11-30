# pricing.py
import datetime
import math
import random

def compute_dynamic_price(base_price: float,
                          seats_total: int,
                          seats_available: int,
                          departure: datetime.datetime,
                          demand_factor: float | None = None
                         ) -> (float, str):
    """
    Compute an adjusted price from the base_price and other inputs.

    Returns:
      (adjusted_price, reason_string)
    """
    # safety
    if seats_total <= 0:
        seats_total = 1
    remaining_pct = seats_available / seats_total  # 0.0 .. 1.0
    hours_to_departure = max((departure - datetime.datetime.utcnow()).total_seconds() / 3600.0, 0.0)

    # demand_factor: external override (0.5 .. 2.0). If None, we simulate a small random demand bump.
    if demand_factor is None:
        demand_factor = 1.0 + (random.random() - 0.4) * 0.3  # roughly 0.7 .. 1.3

    # base multiplier from remaining seats: fewer seats -> higher multiplier
    # Map remaining_pct 1.0 -> 1.0 multiplier, 0.0 -> 2.0 multiplier (you can tune)
    seat_multiplier = 1.0 + (1.0 - remaining_pct) * 1.0  # 1.0 .. 2.0

    # urgency multiplier based on time to departure:
    # far away (>168h) -> no change, near (<24h) -> raise price; use smooth exponential
    if hours_to_departure <= 0:
        time_multiplier = 2.0
    else:
        # use a function that grows as time decreases
        time_multiplier = 1.0 + max(0.0, (48.0 - min(hours_to_departure, 48.0)) / 48.0) * 0.8
        # time_multiplier roughly 1.0 .. 1.8 when inside 48h

    # pricing tiers (avoid huge swings)
    multiplier = seat_multiplier * time_multiplier * demand_factor

    # final price with rounding and a floor
    adj_price = base_price * multiplier

    # apply tiered rounding to look realistic
    if adj_price < 1000:
        adj_price = round(adj_price / 10) * 10
    elif adj_price < 5000:
        adj_price = round(adj_price / 50) * 50
    else:
        adj_price = round(adj_price / 100) * 100

    # ensure not below base (optional)
    adj_price = max(adj_price, base_price * 0.9)

    reason = (f"base={base_price:.2f} seats_pct={remaining_pct:.2f} "
              f"time_h={hours_to_departure:.1f} demand={demand_factor:.2f} "
              f"mult={multiplier:.2f}")
    return float(adj_price), reason
