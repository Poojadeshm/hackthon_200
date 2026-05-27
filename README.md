# hackthon_200
# 🍎 PredictaShelf – Complete Setup Guide

## 📁 Project Structure
```
predictashelf/
├── app.py               ← Flask backend (all routes)
├── translations.py      ← EN / HI / GU translations
├── products.json        ← Sample product data
├── requirements.txt     ← Python dependencies
├── templates/
│   ├── index.html       ← Main dashboard (with AI panel)
│   ├── login.html       ← Login & signup
│   ├── form.html        ← Add item form
│   └── profile.html     ← User profile
└── models/              ← Put trained .pkl files here
    ├── linear_model.pkl
    ├── logistic_model.pkl
    ├── scaler.pkl
    ├── scaler_cls.pkl
    ├── label_encoder.pkl
    ├── kmeans_model.pkl
    ├── scaler_kmeans.pkl
    └── cluster_labels.pkl
```

---

## 🚀 VS Code Mein Run Karo — Step by Step

### Step 1 — VS Code mein folder kholo
```
File → Open Folder → predictashelf folder select karo
```

### Step 2 — PostgreSQL setup karo
```sql
-- pgAdmin ya psql terminal mein:
CREATE DATABASE predictashelf;
-- Password "1234" set karo postgres user ke liye
-- (ya app.py mein password change karo)
```

### Step 3 — Terminal open karo (Ctrl + `)

### Step 4 — Virtual environment banao
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### Step 5 — Dependencies install karo
```bash
pip install -r requirements.txt
```

### Step 6 — ML Models train karo (ek baar, agar models/ folder empty hai)
```bash
# predictashelf folder mein models/ folder banao
mkdir models

# ML trainer scripts se generate karo (from previous project)
python models/generate_data.py
python models/linear_regression.py
python models/logistic_regression.py
python models/clustering.py
```
> ⚠️ Agar models/ nahi hai, AI panel automatically rule-based fallback use karega — sab kuch kaam karega!

### Step 7 — Flask server start karo
```bash
python app.py
```

### Step 8 — Browser mein kholo
```
http://localhost:5000
```

---

## 🔗 Routes / URLs

| URL | Page |
|-----|------|
| `/` → redirects to login | Login page |
| `/dashboard` | Main dashboard with AI panel |
| `/form` | Add new item |
| `/profile` | User profile |
| `/api/predict` | ML prediction API (POST) |
| `/set_lang/en` | Language switch |

---

## 🤖 AI Panel — How It Works

The dashboard has a new **AI Expiry Predictor** panel:

1. **Enter** Temperature, Humidity, Days Since Purchase, Shelf Life
2. **Click Predict** → sends `POST /api/predict` to Flask
3. Flask runs **Linear Regression** (days_left) + **Logistic Regression** (Safe/Warning/Danger)
4. Result shows instantly on dashboard in your **same gold theme**

If ML models not trained → rule-based formula used automatically (no error).

---

## ⚡ Quick Test

```bash
# API test from terminal:
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"temperature":5,"humidity":70,"days_since_purchase":4,"original_shelf_life":7}'

# Expected response:
# {"days_left":2.7,"status":"Warning","confidence":88.0,"group":"Perishable","alert":"⚠️ Use within 2.7 days!","alert_level":"warning"}
```

---

*PredictaShelf — Smart Expiry Tracker 🏺*
