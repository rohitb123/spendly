import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db import get_db


USER_ID = 2
COUNT = 5
MONTHS = 3


CATEGORIES = [
    ("Food", 50, 800, 30, [
        "Lunch at dhaba", "Zomato order", "Swiggy biryani", "Chai and samosa",
        "Dinner with family", "Breakfast - paratha", "Pani puri",
        "Coffee at CCD", "Office canteen meal", "Vada pav",
    ]),
    ("Transport", 20, 500, 20, [
        "Ola cab", "Uber ride", "Metro card recharge", "Auto rickshaw",
        "Petrol", "Bus fare", "Local train ticket",
    ]),
    ("Bills", 200, 3000, 15, [
        "Electricity bill", "Mobile recharge", "Broadband bill",
        "DTH recharge", "Water bill", "Gas cylinder",
    ]),
    ("Health", 100, 2000, 5, [
        "Apollo pharmacy", "Doctor consultation", "Blood test",
        "Dentist visit", "Medicines",
    ]),
    ("Entertainment", 100, 1500, 5, [
        "PVR movie tickets", "Netflix subscription", "Hotstar subscription",
        "Concert tickets", "Bowling night",
    ]),
    ("Shopping", 200, 5000, 15, [
        "Myntra order", "Amazon purchase", "Flipkart order",
        "Big Bazaar groceries", "DMart shopping", "New kurta",
        "Footwear from Bata",
    ]),
    ("Other", 50, 1000, 10, [
        "Donation at temple", "Gift for friend", "Stationery",
        "Haircut at salon", "Laundry",
    ]),
]


def pick_category():
    weights = [c[3] for c in CATEGORIES]
    return random.choices(CATEGORIES, weights=weights, k=1)[0]


def random_date_in_past(months):
    now = datetime.now()
    days = months * 30
    delta_days = random.randint(0, days)
    return (now - timedelta(days=delta_days)).strftime("%Y-%m-%d")


def main():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (USER_ID,))
    if cursor.fetchone() is None:
        conn.close()
        print(f"No user found with id {USER_ID}.")
        sys.exit(1)

    rows = []
    for _ in range(COUNT):
        category, lo, hi, _, descriptions = pick_category()
        amount = round(random.uniform(lo, hi), 2)
        date = random_date_in_past(MONTHS)
        description = random.choice(descriptions)
        rows.append((USER_ID, amount, category, date, description))

    try:
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        print(f"Insert failed, rolled back: {exc}")
        sys.exit(1)

    dates = sorted(r[3] for r in rows)
    print(f"Inserted {len(rows)} expenses for user {USER_ID}.")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print("Sample:")

    cursor.execute(
        "SELECT id, amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (USER_ID,),
    )
    for row in cursor.fetchall():
        print(f"  id={row['id']} ₹{row['amount']:.2f} {row['category']:<13} "
              f"{row['date']}  {row['description']}")

    conn.close()


if __name__ == "__main__":
    main()
