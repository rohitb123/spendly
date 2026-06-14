import os
import random
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from werkzeug.security import generate_password_hash

from database.db import get_db


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Rohan", "Rahul", "Aryan", "Karan", "Kabir", "Aryan",
    "Dhruv", "Yash", "Siddharth", "Rishabh", "Ananya", "Diya", "Aadhya", "Saanvi",
    "Pari", "Anika", "Navya", "Riya", "Myra", "Sara", "Priya", "Neha", "Pooja",
    "Kavya", "Ishita", "Tara", "Meera", "Aishwarya", "Divya", "Shreya",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Patel", "Singh", "Kumar", "Reddy", "Iyer",
    "Nair", "Menon", "Pillai", "Rao", "Naidu", "Mukherjee", "Chatterjee",
    "Banerjee", "Ghosh", "Bose", "Das", "Sen", "Joshi", "Desai", "Mehta",
    "Shah", "Kapoor", "Khanna", "Malhotra", "Chopra", "Bhatia", "Sethi",
    "Aggarwal", "Bansal", "Jain", "Mishra", "Tiwari", "Yadav", "Pandey",
]


def generate_user():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    suffix = random.randint(10, 999)
    email = f"{first.lower()}.{last.lower()}{suffix}@gmail.com"
    return name, email


def main():
    conn = get_db()
    cursor = conn.cursor()

    while True:
        name, email = generate_user()
        cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))
        if cursor.fetchone() is None:
            break

    password_hash = generate_password_hash("password123")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, created_at),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"id: {user_id}")
    print(f"name: {name}")
    print(f"email: {email}")


if __name__ == "__main__":
    main()
