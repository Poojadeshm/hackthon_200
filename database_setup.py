"""
================================================================
  PredictaShelf — database_setup.py
  Run this ONCE to create all tables + insert dummy data
  Command: python database_setup.py
================================================================
"""

import psycopg2
from psycopg2.extras import execute_values
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
import random

# ── Same config as app.py ─────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "database": "predictashelf",
    "user":     "postgres",
    "password": "1234",
    "port":     "5432",
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

# ══════════════════════════════════════════════════════════════
# STEP 1 — CREATE TABLES
# ══════════════════════════════════════════════════════════════
def create_tables(cur):
    print("📋 Creating tables...")

    # USERS table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id             SERIAL PRIMARY KEY,
            email          VARCHAR(255) UNIQUE NOT NULL,
            mobile         VARCHAR(20),
            gender         VARCHAR(20),
            birthday       DATE,
            password_hash  TEXT NOT NULL,
            preferred_lang VARCHAR(5) DEFAULT 'en',
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # PRODUCTS table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id            BIGINT PRIMARY KEY,
            user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name          VARCHAR(255) NOT NULL,
            category      VARCHAR(50),
            expiry        DATE,
            purchase_date DATE,
            note          TEXT,
            price         NUMERIC(10,2) DEFAULT 0,
            added         DATE DEFAULT CURRENT_DATE
        );
    """)

    # SCAN LOG table (barcode scanner ke liye)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scan_log (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
            barcode    VARCHAR(100),
            item_name  VARCHAR(255),
            scan_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ALERTS table (notification history)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
            product_id  BIGINT REFERENCES products(id) ON DELETE CASCADE,
            alert_type  VARCHAR(20),   -- 'gmail' / 'whatsapp' / 'dashboard'
            message     TEXT,
            sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    print("   ✅ Tables created (users, products, scan_log, alerts)")


# ══════════════════════════════════════════════════════════════
# STEP 2 — INSERT DUMMY USERS
# ══════════════════════════════════════════════════════════════
def insert_users(cur):
    print("\n👤 Inserting dummy users...")

    users = [
        # ( email,               mobile,       gender,   birthday,     password,      lang )
        ("demo@predictashelf.com", "9876543210", "female", "1998-05-15", "demo1234",   "en"),
        ("rahul@example.com",      "9823456789", "male",   "1995-11-22", "rahul123",   "hi"),
        ("priya@example.com",      "9712345678", "female", "2000-03-08", "priya456",   "gu"),
        ("test@test.com",          "9000000001", "other",  "1990-01-01", "test1234",   "en"),
    ]

    inserted_ids = []
    for email, mobile, gender, birthday, password, lang in users:
        pwd_hash = generate_password_hash(password)
        try:
            cur.execute("""
                INSERT INTO users (email, mobile, gender, birthday, password_hash, preferred_lang)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id;
            """, (email, mobile, gender, birthday, pwd_hash, lang))
            row = cur.fetchone()
            if row:
                inserted_ids.append(row[0])
                print(f"   ✅ User: {email}  (password: {password})")
            else:
                # Already exists — fetch ID
                cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                inserted_ids.append(cur.fetchone()[0])
                print(f"   ⏩ Already exists: {email}")
        except Exception as e:
            print(f"   ❌ Error inserting {email}: {e}")
            inserted_ids.append(None)

    return inserted_ids   # list of user IDs


# ══════════════════════════════════════════════════════════════
# STEP 3 — INSERT DUMMY PRODUCTS
# ══════════════════════════════════════════════════════════════
def insert_products(cur, user_ids):
    print("\n🛒 Inserting dummy products...")

    today = date.today()

    # Helper: date offset from today
    def d(offset):
        return today + timedelta(days=offset)

    # Format: (name, category, expiry_offset, purchase_offset, note, price)
    #   positive offset = future (not yet expired)
    #   negative offset = past   (already expired → Danger)
    product_templates = [

        # ── FOOD (Danger — already expired) ──────────────────
        ("Milk",          "Food",       -2,   -9,  "Full fat",         52),
        ("Curd",          "Food",       -1,   -8,  "",                 30),
        ("Bread",         "Food",       -3,  -10,  "Brown bread",      45),
        ("Chicken",       "Food",       -1,   -4,  "Fresh cut",       150),
        ("Fish",          "Food",       -2,   -5,  "",                 200),

        # ── FOOD (Warning — expiring in 1–3 days) ────────────
        ("Paneer",        "Food",        1,   -6,  "",                 80),
        ("Butter",        "Food",        2,  -28,  "Amul salted",      55),
        ("Yogurt",        "Food",        1,   -7,  "Low fat",          40),
        ("Cheese Slice",  "Food",        3,  -20,  "Britannia",        90),
        ("Banana",        "Food",        2,   -5,  "1 dozen",          30),

        # ── FOOD (Safe — more than 3 days left) ──────────────
        ("Eggs",          "Food",       10,   -7,  "6 pcs",            70),
        ("Apple",         "Food",       12,   -3,  "Shimla apples",    80),
        ("Tomato",        "Food",        7,   -2,  "",                 25),
        ("Carrot",        "Food",       14,   -5,  "1 kg",             35),
        ("Orange Juice",  "Food",        6,   -1,  "Tropicana",        95),
        ("Mango",         "Food",       21,   -1,  "Alphonso",        120),
        ("Spinach",       "Food",        5,   -2,  "500g",             28),
        ("Potato",        "Food",       30,   -7,  "2 kg",             40),

        # ── GROCERIES ─────────────────────────────────────────
        ("Atta",          "Groceries", 180,  -30,  "5 kg pack",       250),
        ("Rice",          "Groceries", 365,  -60,  "Basmati 5kg",     480),
        ("Dal",           "Groceries", 300,  -20,  "Toor dal 1kg",     90),
        ("Sugar",         "Groceries", 730,  -10,  "1 kg",             45),
        ("Salt",          "Groceries", 900,  -90,  "Tata salt",        20),
        ("Turmeric",      "Groceries", 365,  -45,  "100g",             18),
        ("Mustard Oil",   "Groceries", 270,  -30,  "Fortune 1L",      130),
        ("Ghee",          "Groceries", 365,  -14,  "Amul 500ml",      310),
        ("Biscuits",      "Groceries",  90,  -10,  "Parle-G",          20),
        ("Maggi",         "Groceries", 180,  -15,  "2 min noodles",    14),

        # ── MEDICINE ──────────────────────────────────────────
        ("Paracetamol",   "Medicine",  365,  -30,  "500mg strip",      20),
        ("Cough Syrup",   "Medicine",  180,  -15,  "Benadryl",         95),
        ("Vitamin C",     "Medicine",  270,  -45,  "Limcee 500mg",     85),
        ("Antacid",       "Medicine",  365,  -20,  "Gelusil",          35),
        ("Band-Aid",      "Medicine",  730,  -60,  "Johnson & Johnson",85),

        # ── PERSONAL CARE ─────────────────────────────────────
        ("Shampoo",       "Personal",  365,  -30,  "Head & Shoulders", 220),
        ("Soap",          "Personal",  730,  -45,  "Dettol 4-pack",    80),
        ("Toothpaste",    "Personal",  730,  -20,  "Colgate Max",      65),
        ("Moisturiser",   "Personal",  540,  -60,  "Nivea",           145),
        ("Sunscreen",     "Personal",  365,  -10,  "SPF 50",          280),

        # ── BEVERAGES ─────────────────────────────────────────
        ("Green Tea",     "Beverages", 365,  -30,  "24 bags",         120),
        ("Coffee",        "Beverages", 365,  -45,  "Nescafe 100g",    310),
        ("Coconut Water", "Beverages",   7,   -1,  "Tender coconut",   35),
        ("Cold Drink",    "Beverages",  90,  -14,  "Coca-Cola 2L",     95),

        # ── JEWELRY (no expiry concern — far future) ──────────
        ("Gold Ring",     "Jewelry",  3650,   -30, "22K gold",      45000),
        ("Silver Earring","Jewelry",  3650,  -180, "925 silver",     1200),
        ("Watch",         "Jewelry",  3650,  -365, "Titan Fastrack", 3500),
    ]

    # Distribute products across users
    uid = user_ids[0] if user_ids else 1   # main demo user gets all

    inserted = 0
    for i, (name, cat, exp_off, pur_off, note, price) in enumerate(product_templates):
        prod_id = 1800000000000 + i   # unique bigint ID
        expiry  = d(exp_off)
        purchase= d(pur_off)

        try:
            cur.execute("""
                INSERT INTO products (id, user_id, name, category, expiry, purchase_date, note, price, added)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (prod_id, uid, name, cat, expiry, purchase, note, price, today))
            inserted += 1
        except Exception as e:
            print(f"   ❌ Error: {name} — {e}")

    print(f"   ✅ {inserted} products inserted for user: demo@predictashelf.com")

    # Give user 2 (rahul) a few items too
    if len(user_ids) > 1 and user_ids[1]:
        rahul_items = [
            ("Doodh",   "Food",     1,  -5,  "",  48),
            ("Kela",    "Food",     3,  -4,  "",  25),
            ("Chawal",  "Groceries",365,-30, "5kg",400),
            ("Dahi",    "Food",     2,  -6,  "",  35),
        ]
        for i, (name, cat, exp_off, pur_off, note, price) in enumerate(rahul_items):
            prod_id = 1900000000000 + i
            try:
                cur.execute("""
                    INSERT INTO products (id, user_id, name, category, expiry, purchase_date, note, price, added)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (prod_id, user_ids[1], name, cat, d(exp_off), d(pur_off), note, price, today))
            except Exception as e:
                pass
        print(f"   ✅  4 Hindi items inserted for rahul@example.com")


# ══════════════════════════════════════════════════════════════
# STEP 4 — INSERT DUMMY SCAN LOG
# ══════════════════════════════════════════════════════════════
def insert_scan_log(cur, user_id):
    print("\n📷 Inserting scan log...")
    scans = [
        ("8901030890352", "Amul Milk"),
        ("8901058850056", "Britannia Bread"),
        ("8906007374064", "Lay's Chips"),
        ("8901088014764", "Nestle Yogurt"),
        ("8901063150417", "Parle-G"),
    ]
    for barcode, item in scans:
        cur.execute("""
            INSERT INTO scan_log (user_id, barcode, item_name)
            VALUES (%s, %s, %s);
        """, (user_id, barcode, item))
    print(f"   ✅ {len(scans)} scan records inserted")


# ══════════════════════════════════════════════════════════════
# STEP 5 — INSERT DUMMY ALERTS
# ══════════════════════════════════════════════════════════════
def insert_alerts(cur, user_id):
    print("\n🔔 Inserting alert history...")
    alerts = [
        (1800000000000, "dashboard", "Milk expired — please check"),
        (1800000000001, "gmail",     "Curd expiry alert sent via Gmail"),
        (1800000000002, "whatsapp",  "Bread expiry alert sent via WhatsApp"),
        (1800000000009, "dashboard", "Paneer expiring tomorrow"),
    ]
    for prod_id, atype, msg in alerts:
        try:
            cur.execute("""
                INSERT INTO alerts (user_id, product_id, alert_type, message)
                VALUES (%s, %s, %s, %s);
            """, (user_id, prod_id, atype, msg))
        except Exception:
            pass
    print(f"   ✅ {len(alerts)} alert records inserted")


# ══════════════════════════════════════════════════════════════
# MAIN — Run all steps
# ══════════════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  PredictaShelf — Database Setup")
    print("=" * 55)

    try:
        conn = get_db()
        cur  = conn.cursor()
        print("✅ Connected to PostgreSQL!\n")

        create_tables(cur)
        conn.commit()

        user_ids = insert_users(cur)
        conn.commit()

        insert_products(cur, user_ids)
        conn.commit()

        if user_ids and user_ids[0]:
            insert_scan_log(cur, user_ids[0])
            insert_alerts(cur, user_ids[0])
        conn.commit()

        cur.close()
        conn.close()

        print("\n" + "=" * 55)
        print("  ✅ Database setup complete!")
        print("=" * 55)
        print("\n🔑 Login credentials:")
        print("   Email   : demo@predictashelf.com")
        print("   Password: demo1234")
        print("\n   Email   : rahul@example.com")
        print("   Password: rahul123")
        print("\n   Email   : test@test.com")
        print("   Password: test1234")
        print("\n🚀 Now run: python app.py")
        print("   Open   : http://localhost:5000")

    except psycopg2.OperationalError as e:
        print(f"\n❌ DB Connection failed!\n   Error: {e}")
        print("\n   Check karo:")
        print("   1. PostgreSQL chal raha hai? (pgAdmin open karo)")
        print("   2. Database 'predictashelf' bana hua hai?")
        print("      → pgAdmin mein: CREATE DATABASE predictashelf;")
        print("   3. Password sahi hai? (default: 1234)")
        print("      → database_setup.py line 14 mein change karo")

if __name__ == "__main__":
    main()
