from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date, timedelta
from translations import TRANSLATIONS
import json, os, psycopg2, psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "predictashelf2025"


# ── DATABASE CONNECTION ────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host="localhost",
        database="predictashelf",
        user="postgres",
        password="1234",
        port="5432"
    )

def init_db():
    """Create tables if they don't exist"""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            mobile VARCHAR(20),
            gender VARCHAR(20),
            birthday DATE,
            password_hash TEXT NOT NULL,
            preferred_lang VARCHAR(5) DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id BIGINT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(50),
            expiry DATE,
            purchase_date DATE,
            note TEXT,
            price NUMERIC(10,2) DEFAULT 0,
            added DATE DEFAULT CURRENT_DATE
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# ── LOGIN REQUIRED DECORATOR ───────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("error|Please login first!")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── LANGUAGE HELPER ────────────────────────────────────────────────────────
def get_lang():
    return session.get("lang", "en")


# ── LANGUAGE SWITCHER ROUTE ────────────────────────────────────────────────
@app.route("/set_lang/<lang>")
def set_lang(lang):
    """Switch language and save to session (and DB if logged in)"""
    if lang in ("en", "hi", "gu"):
        session["lang"] = lang
        if "user_id" in session:
            try:
                conn = get_db()
                cur  = conn.cursor()
                cur.execute(
                    "UPDATE users SET preferred_lang = %s WHERE id = %s",
                    (lang, session["user_id"])
                )
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                pass
    return redirect(request.referrer or url_for("index"))


# ── SHELF LIFE DATA ────────────────────────────────────────────────────────
SHELF_LIFE = {
    "milk":3,"doodh":3,"dudh":3,"cream":5,"butter":30,"cheese":14,
    "paneer":4,"yogurt":7,"dahi":5,"curd":5,"bread":6,"pav":4,"roti":2,
    "egg":21,"anda":21,"inda":21,"chicken":2,"mutton":2,"fish":2,
    "tomato":5,"tamatar":5,"onion":30,"pyaz":30,"dungri":30,
    "potato":14,"aloo":14,"batata":14,"carrot":10,"gajar":10,
    "spinach":4,"palak":4,"cabbage":7,"capsicum":7,"broccoli":5,
    "apple":14,"seb":14,"banana":5,"kela":5,"kandu":5,
    "mango":5,"aam":5,"keri":5,"orange":10,"grapes":7,"papaya":5,
    "juice":3,"rice":365,"chawal":365,"flour":180,"atta":180,
    "maida":180,"oil":365,"tel":365,"ghee":180,"sugar":730,
    "dal":180,"noodles":180,"maggi":180,"pasta":365,
    "biscuit":90,"chocolate":180,"chips":60,"sauce":30,
    "ketchup":30,"pickle":180,"jam":90,"honey":730,
    "moisturizer":365,"lotion":365,"sunscreen":180,
    "face wash":365,"toner":365,"serum":365,"scrub":180,
    "lipstick":365,"lip gloss":180,"foundation":180,
    "mascara":90,"kajal":180,"eyeliner":180,"eyeshadow":730,
    "shampoo":365,"conditioner":365,"hair oil":365,
    "body wash":365,"soap":365,"deodorant":365,"perfume":730,
    "nail polish":365,"tablet":365,"capsule":365,"syrup":180,
    "ointment":365,"tea":730,"coffee":365,"oats":365,
    "default_Food":7,"default_Cosmetics":365,"default_Beauty":365,
    "default_Medicine":365,"default_Groceries":90,"default_Grocery":90,
    "default_Jewelry":730,
}

JEWELRY_OXIDATION = {
    "silver": {"icon": "🥈", "stages": [
        {"days": 0,   "en": "Brand New",     "hi": "बिल्कुल नया",  "gu": "બિલ્કુલ નવું",
         "color_en": "Brilliant silver shine", "color_hi": "चमकदार चांदी",  "color_gu": "ચળકતી ચાંદી",
         "care_en": "Keep in anti-tarnish pouch. Avoid moisture.",
         "care_hi": "एंटी-टार्निश पाउच में रखें। नमी से बचाएं।",
         "care_gu": "એન્ટી-ટાર્નિશ પાઉચમાં રાખો.", "pct": 100, "dot": "#e8e8e8"},
        {"days": 90,  "en": "Light Tarnish",  "hi": "हल्का कालापन", "gu": "હળવો ડાઘ",
         "color_en": "Yellowish tint",          "color_hi": "पीलापन",          "color_gu": "પીળાશ",
         "care_en": "Baking soda + water paste gently.",
         "care_hi": "बेकिंग सोडा + पानी का पेस्ट।",
         "care_gu": "બેકિંગ સોડા + પાણીનો પેસ્ટ.", "pct": 65, "dot": "#c8c0a0"},
        {"days": 270, "en": "Heavy Tarnish",  "hi": "बहुत काली",    "gu": "ઘણી કાળી",
         "color_en": "Dark brown coating",      "color_hi": "गहरा भूरा",       "color_gu": "ઘેરો ભૂરો",
         "care_en": "Professional cleaning needed.",
         "care_hi": "प्रोफेशनल सफाई जरूरी।",
         "care_gu": "પ્રૉફેશનલ સફાઈ જરૂરી.", "pct": 25, "dot": "#806040"},
        {"days": 365, "en": "Oxidized",        "hi": "पूरी काली",    "gu": "સંપૂર્ણ કાળી",
         "color_en": "Fully black oxidized",    "color_hi": "पूरी तरह काली",   "color_gu": "સંપૂર્ણ કાળી",
         "care_en": "Silver dip cleaner needed.",
         "care_hi": "सिल्वर डिप क्लीनर जरूरी।",
         "care_gu": "સિલ્વર ડિપ ક્લીનર.", "pct": 10, "dot": "#333"},
    ]},
    "gold": {"icon": "🥇", "stages": [
        {"days": 0,   "en": "Brand New",  "hi": "बिल्कुल नया", "gu": "બિલ્કુલ નવું",
         "color_en": "Brilliant warm gold", "color_hi": "चमकदार सोना", "color_gu": "ચળકતું સોનું",
         "care_en": "Avoid harsh chemicals.", "care_hi": "कठोर रसायनों से बचें।",
         "care_gu": "કઠોર રસાયણોથી બચો.", "pct": 100, "dot": "#f0d060"},
        {"days": 180, "en": "Dull Sheen", "hi": "फीकी चमक",    "gu": "ઝાંખી ચળકાટ",
         "color_en": "Less reflective",    "color_hi": "कम चमकदार",   "color_gu": "ઓછી ચળકાટ",
         "care_en": "Warm soapy water clean.", "care_hi": "गर्म साबुन पानी से साफ।",
         "care_gu": "ગરમ સાબુ પાણીથી સાફ.", "pct": 72, "dot": "#c09830"},
        {"days": 730, "en": "Faded",      "hi": "बहुत फीकी",   "gu": "ઘણી ઝાંખી",
         "color_en": "Base metal showing", "color_hi": "नीचे की धातु दिख रही", "color_gu": "નીચેની ધાતુ દેખાય",
         "care_en": "Re-plating may be needed.", "care_hi": "री-प्लेटिंग की जरूरत।",
         "care_gu": "ફરી પ્લેટિંગ.", "pct": 30, "dot": "#806010"},
    ]},
    "copper": {"icon": "🟤", "stages": [
        {"days": 0,   "en": "Brand New",    "hi": "बिल्कुल नया", "gu": "બિલ્કુલ નવું",
         "color_en": "Bright reddish-orange", "color_hi": "लाल-नारंगी", "color_gu": "લાલ-નારંગી",
         "care_en": "Apply clear nail polish.", "care_hi": "क्लियर नेल पॉलिश लगाएं।",
         "care_gu": "ક્લિયર નેઇલ પૉલિશ.", "pct": 100, "dot": "#e07040"},
        {"days": 90,  "en": "Dark Brown",   "hi": "गहरा भूरा",  "gu": "ઘેરો ભૂરો",
         "color_en": "Brown patches",        "color_hi": "भूरे धब्बे",  "color_gu": "ભૂરા ડાઘ",
         "care_en": "Ketchup rub works!", "care_hi": "केचप रगड़ें!", "care_gu": "કેચઅપ ઘસો!",
         "pct": 35, "dot": "#602810"},
        {"days": 180, "en": "Green Patina", "hi": "हरा रंग",    "gu": "લીલો ડાઘ",
         "color_en": "Green verdigris",      "color_hi": "हरा-नीला",    "color_gu": "લીલો-વાદળી",
         "care_en": "Vinegar + salt paste.", "care_hi": "सिरका + नमक पेस्ट।",
         "care_gu": "સરકો + મીઠું.", "pct": 15, "dot": "#406040"},
    ]},
}

RECIPES = {
    "milk": [
        {"name_en": "Kheer",           "name_hi": "खीर",           "name_gu": "ખીર",
         "time": "30 min", "emoji": "🍚", "ingredients": "Milk, Rice, Sugar, Cardamom",
         "tip_en": "Full-fat milk gives creamier texture.",
         "tip_hi": "मलाईदार खीर के लिए फुल-फैट दूध।",
         "tip_gu": "ક્રીમી ખીર માટે ફુલ-ફેટ દૂધ."},
        {"name_en": "Homemade Paneer", "name_hi": "घर का पनीर",   "name_gu": "ઘરનું પનીર",
         "time": "20 min", "emoji": "🧀", "ingredients": "Milk, Lemon juice",
         "tip_en": "Boil milk, add lemon, strain.",
         "tip_hi": "दूध उबालें, नींबू डालें, छानें।",
         "tip_gu": "દૂધ ઉકાળો, લીંબુ નાખો, ગાળો."},
        {"name_en": "Chai",            "name_hi": "चाय",            "name_gu": "ચા",
         "time": "5 min",  "emoji": "☕", "ingredients": "Milk, Tea, Sugar, Ginger",
         "tip_en": "Add cardamom for masala flavor.",
         "tip_hi": "इलायची डालें मसाला के लिए।",
         "tip_gu": "મસાલા ચા માટે એલચી ઉમેરો."},
    ],
    "bread": [
        {"name_en": "French Toast", "name_hi": "फ्रेंच टोस्ट", "name_gu": "ફ્રેન્ચ ટોસ્ટ",
         "time": "10 min", "emoji": "🍞", "ingredients": "Bread, Egg, Milk, Sugar",
         "tip_en": "Soak bread 30 seconds each side.",
         "tip_hi": "30 सेकंड दोनों तरफ भिगोएं।",
         "tip_gu": "30 સેકન્ડ બંને બાજુ ડૂબાડો."},
        {"name_en": "Bread Pakora", "name_hi": "ब्रेड पकोड़ा",  "name_gu": "બ્રેડ ભજિયાં",
         "time": "20 min", "emoji": "🟡", "ingredients": "Bread, Besan, Potato, Spices",
         "tip_en": "Add ajwain to batter.",
         "tip_hi": "बेसन में अजवाइन डालें।",
         "tip_gu": "ખીરામાં અજમો ઉમેરો."},
    ],
    "egg": [
        {"name_en": "Masala Omelette", "name_hi": "मसाला ऑमलेट", "name_gu": "મસાલા ઑમ્લેટ",
         "time": "8 min",  "emoji": "🍳", "ingredients": "Eggs, Onion, Tomato, Chilli",
         "tip_en": "Add water for fluffier omelette.",
         "tip_hi": "फुलाने के लिए थोड़ा पानी।",
         "tip_gu": "ફ્લફી માટે થોડું પાણી."},
        {"name_en": "Egg Bhurji",      "name_hi": "अंडा भुर्जी",  "name_gu": "ઇંડા ભૂર્જી",
         "time": "12 min", "emoji": "🥘", "ingredients": "Eggs, Onion, Tomato, Spices",
         "tip_en": "Low heat, stir constantly.",
         "tip_hi": "धीमी आंच, लगातार हिलाएं।",
         "tip_gu": "ધીમી આંચ, સતત હલાવો."},
    ],
    "banana": [
        {"name_en": "Banana Smoothie", "name_hi": "केला स्मूदी",  "name_gu": "કેળાની સ્મૂધી",
         "time": "5 min",  "emoji": "🥤", "ingredients": "Banana, Milk, Honey, Ice",
         "tip_en": "Freeze overripe bananas.",
         "tip_hi": "ज्यादा पके केले फ्रीज करें।",
         "tip_gu": "વધારે પાકેલ કેળ ફ્રીઝ કરો."},
    ],
    "yogurt": [
        {"name_en": "Raita", "name_hi": "रायता", "name_gu": "રાઈતું",
         "time": "5 min",  "emoji": "🥗", "ingredients": "Yogurt, Cucumber, Cumin, Salt",
         "tip_en": "Squeeze cucumber water first.",
         "tip_hi": "खीरे का पानी निचोड़ें।",
         "tip_gu": "કાકડીનું પાણી નિચોવો."},
        {"name_en": "Lassi", "name_hi": "लस्सी",  "name_gu": "લસ્સી",
         "time": "5 min",  "emoji": "🥛", "ingredients": "Yogurt, Sugar, Cardamom, Ice",
         "tip_en": "Sweet: rose water. Salty: cumin.",
         "tip_hi": "मीठी: गुलाब जल। नमकीन: जीरा।",
         "tip_gu": "મીઠી: ગુલાબ જળ. ખારી: જીરૂ."},
    ],
}

TOXIC_INFO = {
    "Food":      [{"name": "MSG (E621)",          "risk": "high"},
                  {"name": "Sodium Benzoate",      "risk": "moderate"},
                  {"name": "Artificial Colors",    "risk": "high"},
                  {"name": "Trans Fat",            "risk": "high"}],
    "Beauty":    [{"name": "Parabens",             "risk": "high"},
                  {"name": "SLS/SLES",             "risk": "moderate"},
                  {"name": "Formaldehyde",         "risk": "critical"},
                  {"name": "Mercury",              "risk": "critical"}],
    "Cosmetics": [{"name": "Parabens",             "risk": "high"},
                  {"name": "SLS/SLES",             "risk": "moderate"},
                  {"name": "Formaldehyde",         "risk": "critical"},
                  {"name": "Mercury",              "risk": "critical"}],
    "Groceries": [{"name": "BHA/BHT",              "risk": "moderate"},
                  {"name": "Sodium Nitrate",       "risk": "high"}],
    "Grocery":   [{"name": "BHA/BHT",              "risk": "moderate"},
                  {"name": "Sodium Nitrate",       "risk": "high"}],
    "Medicine":  [{"name": "Expired Compounds",    "risk": "critical"}],
    "Jewelry":   [{"name": "Nickel Allergy",       "risk": "high"},
                  {"name": "Lead",                 "risk": "critical"},
                  {"name": "Cadmium",              "risk": "critical"}],
}

# ── CATEGORY MAPS ──────────────────────────────────────────────────────────
# Normalize any variant to standard internal name
CAT_NORMALIZE = {
    "Cosmetics": "Beauty",
    "Grocery":   "Groceries",
}

# Map standard category -> translation key for label
CAT_LABEL_KEY = {
    "Food":      "cat_label_food",
    "Beauty":    "cat_label_beauty",
    "Groceries": "cat_label_groceries",
    "Medicine":  "cat_label_medicine",
    "Jewelry":   "cat_label_jewelry",
}

# Map standard category -> emoji icon
CAT_ICON = {
    "Food":      "🍎",
    "Beauty":    "💄",
    "Groceries": "🛒",
    "Medicine":  "💊",
    "Jewelry":   "💍",
}

# Map standard category -> CSS class name (for filter matching)
CAT_FILTER_KEY = {
    "Food":      "food",
    "Beauty":    "beauty",
    "Groceries": "groceries",
    "Medicine":  "medicine",
    "Jewelry":   "jewelry",
}


# ── HELPER FUNCTIONS ───────────────────────────────────────────────────────
def auto_shelf_days(name, category):
    nl = name.lower()
    for k, v in SHELF_LIFE.items():
        if not k.startswith("default_") and k in nl:
            return v
    return SHELF_LIFE.get(f"default_{category}", 7)

def detect_metal(name):
    nl = name.lower()
    for m in ["silver", "gold", "platinum", "copper", "brass"]:
        if m in nl:
            return m
    if any(x in nl for x in ["chandi", "चांदी", "ચાંદી"]):  return "silver"
    if any(x in nl for x in ["sona",   "सोना",  "સોનું"]):  return "gold"
    if any(x in nl for x in ["tamba",  "तांबा", "તાંબુ"]):  return "copper"
    return None

def detect_jewelry_type(name):
    nl = name.lower()
    types = {
        "earring": "🪬", "vali": "🪬", "bali": "🪬",
        "necklace": "📿", "haar": "📿",
        "bracelet": "💫", "bangle": "💫",
        "ring": "💍", "anklet": "✨", "chain": "⛓️", "pendant": "💎",
    }
    for k, v in types.items():
        if k in nl:
            return k, v
    return "jewelry", "💍"

def get_jewelry_stage(metal, days_owned):
    if metal not in JEWELRY_OXIDATION:
        return None
    stages = JEWELRY_OXIDATION[metal]["stages"]
    cur = stages[0]
    for s in stages:
        if days_owned >= s["days"]:
            cur = s
    return cur

def get_status(expiry_str):
    try:
        exp   = datetime.strptime(str(expiry_str), "%Y-%m-%d").date()
        today = date.today()
        diff  = (exp - today).days
        lang  = get_lang()
        T     = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
        if diff < 0:
            return "expired",  abs(diff), T.get("notif_expired",  "Expired").replace("{n}", str(abs(diff)))
        elif diff == 0:
            return "today",    0,         T.get("notif_today",    "Expires today!")
        elif diff <= 2:
            return "critical", diff,      T.get("auto_expiry_critical", "Only {n} days!").replace("{n}", str(diff))
        elif diff <= 7:
            return "warning",  diff,      T.get("auto_expiry_warning",  "{n} days remaining").replace("{n}", str(diff))
        else:
            return "good",     diff,      T.get("auto_expiry_good",     "{n} days fresh").replace("{n}", str(diff))
    except:
        return "unknown", 0, ""

def get_recipes_for(name):
    nl = name.lower()
    for k, v in RECIPES.items():
        if k in nl:
            return v
    return []

def get_notifications(products):
    notifs = []
    today  = date.today()
    lang   = get_lang()
    T      = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    for p in products:
        try:
            exp  = datetime.strptime(str(p["expiry"]), "%Y-%m-%d").date()
            diff = (exp - today).days
            recipes = get_recipes_for(p["name"])
            rname   = recipes[0].get(f"name_{lang}", recipes[0]["name_en"]) if recipes else ""
            rtxt    = f" {T.get('try_making', '')} {rname}!" if rname else ""
            if diff < 0:
                notifs.append({"type": "expired",  "icon": "💀",
                    "title": f"{p['name']} — {T.get('notif_expired','').replace('{n}', str(abs(diff)))}",
                    "msg":   T.get("notif_expired_msg", "Discard immediately!")})
            elif diff == 0:
                notifs.append({"type": "critical", "icon": "🚨",
                    "title": f"{p['name']} — {T.get('notif_today', '')}",
                    "msg":   T.get("notif_today_msg", "Use right now!") + rtxt})
            elif diff == 1:
                notifs.append({"type": "warning",  "icon": "⚠️",
                    "title": f"{p['name']} — {T.get('notif_tomorrow', '')}",
                    "msg":   T.get("notif_tomorrow_msg", "Last chance!") + rtxt})
            elif diff <= 3:
                notifs.append({"type": "soon",     "icon": "🕐",
                    "title": f"{p['name']} — {T.get('notif_soon', '').replace('{n}', str(diff))}",
                    "msg":   T.get("notif_soon_msg", "Plan to use this week.") + rtxt})
            # Jewelry oxidation notification
            if p.get("category") == "Jewelry" and p.get("purchase_date"):
                pd = datetime.strptime(str(p["purchase_date"]), "%Y-%m-%d").date()
                days_owned = (today - pd).days
                metal = detect_metal(p["name"])
                if metal:
                    stage = get_jewelry_stage(metal, days_owned)
                    if stage and stage["pct"] <= 50:
                        notifs.append({"type": "jewelry", "icon": JEWELRY_OXIDATION[metal]["icon"],
                            "title": f"{p['name']} — {T.get('notif_jewelry', 'Needs attention')}",
                            "msg":   stage.get(f"care_{lang}", stage["care_en"])})
        except:
            pass
    return notifs


# ── AUTH ROUTES ────────────────────────────────────────────────────────────
@app.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("index"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    lang = get_lang()
    T    = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            conn = get_db()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close(); conn.close()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"]    = user["id"]
                session["user_email"] = user["email"]
                session["lang"]       = user["preferred_lang"] or "en"
                flash(f"success|{T.get('login_success', 'Welcome back!')} 👋")
                return redirect(url_for("index"))
            else:
                flash(f"error|{T.get('login_error', 'Invalid email or password!')}")
        except Exception as e:
            flash(f"error|Database error: {str(e)}")
    return render_template("login.html", lang=lang, T=T, TRANSLATIONS=TRANSLATIONS)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    lang = get_lang()
    T    = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    if request.method == "POST":
        email    = request.form.get("email",            "").strip().lower()
        mobile   = request.form.get("mobile",           "").strip()
        gender   = request.form.get("gender",           "")
        birthday = request.form.get("birthday",         "")
        password = request.form.get("password",         "")
        confirm  = request.form.get("confirm_password", "")
        if password != confirm:
            flash(f"error|{T.get('password_mismatch', 'Passwords do not match!')}")
            return redirect(url_for("signup"))
        if len(password) < 6:
            flash(f"error|{T.get('password_short', 'Password must be at least 6 characters!')}")
            return redirect(url_for("signup"))
        try:
            conn = get_db()
            cur  = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                flash(f"error|{T.get('email_exists', 'Email already registered!')}")
                cur.close(); conn.close()
                return redirect(url_for("signup"))
            hashed = generate_password_hash(password)
            cur.execute("""
                INSERT INTO users (email, mobile, gender, birthday, password_hash, preferred_lang)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (email, mobile, gender, birthday or None, hashed, lang))
            user_id = cur.fetchone()[0]
            conn.commit(); cur.close(); conn.close()
            session["user_id"]    = user_id
            session["user_email"] = email
            session["lang"]       = lang
            flash(f"success|{T.get('signup_success', 'Account created! Welcome!')} 🎉")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"error|Database error: {str(e)}")
    return render_template("signup.html", lang=lang, T=T, TRANSLATIONS=TRANSLATIONS)


# ══════════════════════════════════════════════════════════
# AI / ML PREDICTION ROUTE
# ══════════════════════════════════════════════════════════
# This endpoint is called by the AI panel in index.html
# via fetch('/api/predict', {method:'POST', ...})
# ══════════════════════════════════════════════════════════
import os as _os

def _load_models():
    """Load scikit-learn models from models/ folder (lazy, once)."""
    try:
        import joblib
        _base = _os.path.join(_os.path.dirname(__file__), "models")
        return {
            "linear":   joblib.load(_os.path.join(_base, "linear_model.pkl")),
            "logistic": joblib.load(_os.path.join(_base, "logistic_model.pkl")),
            "scaler_lr": joblib.load(_os.path.join(_base, "scaler.pkl")),
            "scaler_cls":joblib.load(_os.path.join(_base, "scaler_cls.pkl")),
            "le":        joblib.load(_os.path.join(_base, "label_encoder.pkl")),
            "kmeans":    joblib.load(_os.path.join(_base, "kmeans_model.pkl")),
            "scaler_km": joblib.load(_os.path.join(_base, "scaler_kmeans.pkl")),
            "cl_labels": joblib.load(_os.path.join(_base, "cluster_labels.pkl")),
        }
    except Exception as e:
        app.logger.warning(f"ML models not loaded (run train scripts first): {e}")
        return None

_ML = None   # loaded on first request


@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    lang   = get_lang()
    T      = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    name   = request.form.get("name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE users SET mobile = %s WHERE id = %s",
            (mobile or None, session["user_id"])
        )
        conn.commit(); cur.close(); conn.close()
        flash(f"success|Profile updated!")
    except Exception as e:
        flash(f"error|Update failed: {str(e)}")
    return redirect(url_for("profile"))

@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    AI Expiry Prediction API — called by the dashboard AI panel.

    Request JSON:
        { temperature, humidity, days_since_purchase, original_shelf_life }

    Response JSON:
        { days_left, status, confidence, group, alert, alert_level }
    """
    global _ML
    data = request.get_json(silent=True) or {}

    try:
        temp  = float(data.get("temperature",         4.5))
        hum   = float(data.get("humidity",            65.0))
        days  = int(data.get("days_since_purchase",   0))
        shelf = int(data.get("original_shelf_life",   7))
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    # ── Try ML models first ──────────────────────────────────
    if _ML is None:
        _ML = _load_models()

    if _ML:
        try:
            feats = [[temp, hum, days, shelf]]
            X_lr  = _ML["scaler_lr"].transform(feats)
            dl    = round(float(_ML["linear"].predict(X_lr)[0]), 1)

            X_cls = _ML["scaler_cls"].transform(feats)
            pred  = _ML["logistic"].predict(X_cls)[0]
            proba = _ML["logistic"].predict_proba(X_cls)[0]
            status     = _ML["le"].inverse_transform([pred])[0]
            confidence = round(float(proba.max()) * 100, 1)

            X_km = _ML["scaler_km"].transform([[temp, hum, days, shelf, dl]])
            cid  = int(_ML["kmeans"].predict(X_km)[0])
            grp  = _ML["cl_labels"].get(cid, "Moderate")
        except Exception as e:
            app.logger.error(f"ML predict error: {e}")
            _ML = None   # reset so rule-based kicks in

    # ── Rule-based fallback (if models not trained yet) ──────
    if _ML is None:
        dl     = round(shelf - days - (max(0, temp - 6) * 0.3) - (max(0, hum - 75) * 0.05), 1)
        status = "Safe" if dl > 3 else "Warning" if dl > 0 else "Danger"
        confidence = 80.0
        grp    = "Moderate"

    alert_map = {
        "Safe":    f"✅ Item is fresh — {dl} days remaining.",
        "Warning": f"⚠️ Use within {dl} days before it spoils!",
        "Danger":  "🔴 Expired or critical! Use immediately or discard.",
    }

    return jsonify({
        "days_left":   dl,
        "status":      status,
        "confidence":  confidence,
        "group":       grp,
        "alert":       alert_map.get(status, ""),
        "alert_level": status.lower(),
    })


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── PROFILE ROUTE ──────────────────────────────────────────────────────────
@app.route("/profile")
@login_required
def profile():
    lang = get_lang()
    T    = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
        user_row = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS cnt FROM products WHERE user_id = %s",
                    (session["user_id"],))
        total_items = cur.fetchone()["cnt"]
        cur.close(); conn.close()

        user = {
            "name":        user_row["email"].split("@")[0],
            "email":       user_row["email"],
            "mobile":      user_row["mobile"]   or "",
            "gender":      user_row["gender"]   or "",
            "birthday":    str(user_row["birthday"]) if user_row["birthday"] else "",
            "preferred_lang": user_row["preferred_lang"] or "en",
            "created":     str(user_row["created_at"])[:10] if user_row["created_at"] else "",
            "total_items": total_items,
        }
    except Exception as e:
        flash(f"error|Profile load error: {str(e)}")
        user = {
            "name": session.get("user_email", "").split("@")[0],
            "email": session.get("user_email", ""),
            "total_items": 0,
        }
    return render_template("profile.html", user=user, lang=lang, T=T,
                           TRANSLATIONS=TRANSLATIONS,
                           user_email=session.get("user_email", ""))


# ── MAIN APP ROUTES ────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def index():
    lang  = get_lang()
    T     = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    today = date.today()
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products WHERE user_id = %s ORDER BY expiry ASC",
                    (session["user_id"],))
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        flash(f"error|DB Error: {str(e)}")
        rows = []

    products = []
    for p in rows:
        pd = dict(p)
        pd["expiry"]        = str(pd["expiry"])
        pd["purchase_date"] = str(pd["purchase_date"]) if pd["purchase_date"] else ""
        status, days, msg   = get_status(pd["expiry"])
        pd["status"]        = status
        pd["days_left"]     = days
        pd["status_msg"]    = msg

        # ── FIX: Normalize category to standard name ──
        raw_cat = pd.get("category", "Food") or "Food"
        pd["category"] = CAT_NORMALIZE.get(raw_cat, raw_cat)

        # ── FIX: Add translated label, icon, and filter key ──
        pd["category_label"]  = T.get(CAT_LABEL_KEY.get(pd["category"], ""), pd["category"])
        pd["category_icon"]   = CAT_ICON.get(pd["category"], "📦")
        pd["category_filter"] = CAT_FILTER_KEY.get(pd["category"], pd["category"].lower())

        pd["recipes"] = get_recipes_for(pd["name"]) if pd.get("category") in ["Food", "Groceries"] else []
        pd["toxic"]   = TOXIC_INFO.get(pd.get("category", "Food"), [])

        if pd.get("category") == "Jewelry":
            metal = detect_metal(pd["name"])
            _, jicon = detect_jewelry_type(pd["name"])
            pd["metal"] = metal
            pd["jicon"] = jicon
            if metal and pd["purchase_date"]:
                try:
                    pdate = datetime.strptime(pd["purchase_date"], "%Y-%m-%d").date()
                    pd["days_owned"]    = (today - pdate).days
                    pd["oxidation"]     = JEWELRY_OXIDATION.get(metal)
                    pd["current_stage"] = get_jewelry_stage(metal, pd["days_owned"])
                except:
                    pass
        products.append(pd)

    products.sort(key=lambda x: (
        0 if x["status"] == "expired"  else
        1 if x["status"] == "today"    else
        2 if x["status"] == "critical" else
        3 if x["status"] == "warning"  else 4
    ))

    notifications = get_notifications(products)
    return render_template("index.html",
        products=products,
        notifications=notifications,
        total=len(products),
        expired=sum(1 for p in products if p["status"] == "expired"),
        critical=sum(1 for p in products if p["status"] in ["today", "critical"]),
        good=sum(1 for p in products if p["status"] == "good"),
        jewelry=sum(1 for p in products if p.get("category") == "Jewelry"),
        lang=lang, T=T, TRANSLATIONS=TRANSLATIONS,
        user_email=session.get("user_email", ""))

@app.route("/form")
@login_required
def form():
    lang = get_lang()
    return render_template("form.html", lang=lang,
                           T=TRANSLATIONS.get(lang, TRANSLATIONS["en"]),
                           TRANSLATIONS=TRANSLATIONS)

@app.route("/add", methods=["POST"])
@login_required
def add_product():
    lang = get_lang()
    T    = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    name            = request.form.get("name",            "").strip()
    category        = request.form.get("category",        "Food")
    purchase        = request.form.get("purchase_date",   "") or date.today().strftime("%Y-%m-%d")
    expiry_override = request.form.get("expiry_override", "")
    note            = request.form.get("note",            "").strip()
    price           = request.form.get("price",           "0") or "0"
    if not name:
        flash(f"error|{T.get('flash_error_name', 'Item name required!')}")
        return redirect(url_for("form"))
    if expiry_override:
        expiry = expiry_override
    else:
        try:
            pd = datetime.strptime(purchase, "%Y-%m-%d").date()
        except:
            pd = date.today()
        expiry = (pd + timedelta(days=auto_shelf_days(name, category))).strftime("%Y-%m-%d")
    try:
        conn = get_db()
        cur  = conn.cursor()
        pid  = int(datetime.now().timestamp() * 1000)
        cur.execute("""
            INSERT INTO products (id, user_id, name, category, expiry, purchase_date, note, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (pid, session["user_id"], name, category, expiry, purchase, note, float(price)))
        conn.commit(); cur.close(); conn.close()
        flash(f"success|{name} {T.get('flash_success', 'added!')} Expiry: {expiry}")
    except Exception as e:
        flash(f"error|DB Error: {str(e)}")
    return redirect(url_for("index"))

@app.route("/delete/<int:pid>")
@login_required
def delete_product(pid):
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s AND user_id = %s",
                    (pid, session["user_id"]))
        conn.commit(); cur.close(); conn.close()
    except:
        pass
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)