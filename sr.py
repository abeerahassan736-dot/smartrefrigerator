from flask import Flask, request, redirect
import random
from datetime import date
import cv2
from pyzbar.pyzbar import decode
from PIL import Image
import sqlite3
import pyttsx3

app = Flask(__name__)
def scan_qr(image_path):
    image = Image.open(image_path)
    results = decode(image)

    if results:
        return results[0].data.decode("utf-8")

    return "No QR code detected"

# Temporary food storage
foods = []

spoken_warnings = set()
def init_database():
    connection = sqlite3.connect("refrigerator.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            expiry TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_database()
def load_foods():
    connection = sqlite3.connect("refrigerator.db")
    cursor = connection.cursor()

    cursor.execute("SELECT id, name, expiry FROM foods")
    rows = cursor.fetchall()

    connection.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "expiry": row[2]
        }
        for row in rows
    ]
meal_suggestions = []


def get_inside_temperature():
    return round(random.uniform(2.0, 7.0), 1)


def get_outside_temperature():
    return round(random.uniform(20.0, 40.0), 1)


def get_humidity():
    return round(random.uniform(45.0, 70.0), 1)


def get_door_status():
    return random.choice(["OPEN", "CLOSED"])


def get_cooling_level(inside, outside, door):
    cooling = 0

    # Keep the inside temperature around 4°C
    if inside > 4:
        cooling += (inside - 4) * 25
    else:
        cooling += 10

    # Hot outside air makes cooling harder
    if outside > 30:
        cooling += 15

    # Opening the door lets warm air inside
    if door == "OPEN":
        cooling += 20

    return min(round(cooling, 1), 100)


@app.route("/api/sensors")
def sensors():
    inside = get_inside_temperature()
    outside = get_outside_temperature()
    humidity = get_humidity()
    door = get_door_status()

    cooling = get_cooling_level(
        inside,
        outside,
        door
    )

    return {
        "inside": inside,
        "outside": outside,
        "humidity": humidity,
        "door": door,
        "cooling": cooling
    }


def speak(message):
    engine = pyttsx3.init()
    engine.say(message)
    engine.runAndWait()    


@app.route("/")
def home():

    inside = get_inside_temperature()
    outside = get_outside_temperature()
    humidity = get_humidity()
    door = get_door_status()

    cooling = get_cooling_level(
        inside,
        outside,
        door
    )

    food_html = ""
    foods_from_database = load_foods()
    suggestions = []
    soon_foods = []

    if len(foods) == 0:
        food_html = "<p>No food added yet.</p>"

    else:
        for food in foods_from_database:
            expiry_date = date.fromisoformat(food["expiry"])
            days_left = (expiry_date - date.today()).days
            if days_left <= 3:
                soon_foods.append(food["name"])

            if days_left < 0:
                expiry_text = "⚠️ EXPIRED"
            elif days_left == 0:
                expiry_text = "🚨 EXPIRES TODAY"
            elif days_left <= 3:
                expiry_text = f"⚠️ USE SOON — {days_left} days left"

                if food["name"] not in spoken_warnings:
                    speak(f"{food['name']} expires in {days_left} days.")
                    spoken_warnings.add(food["name"])
            else:
                expiry_text = f"Expires in {days_left} days"

            food_html += f"""
            <div class="food">
                <strong>📦 {food["name"]}</strong>
                <br>
                {expiry_text}
                <br>
                Expiry date: {food["expiry"]}

                <form action="/delete-food/{food["id"]}" method="POST">
                    <button type="submit">🗑️ Delete</button>
                </form>
            </div>
            """
        if foods_from_database:
            food_names = [food["name"].lower() for food in foods_from_database]
            if soon_foods:
                suggestions.append(
                    "⚠️ Use soon: " + ", ".join(soon_foods)
                )

            if "egg" in " ".join(food_names) and "bread" in " ".join(food_names):
                if "egg" in " ".join(soon_foods):
                    suggestions.append("🍳 Egg toast — use the eggs soon!")
                else:
                    suggestions.append("🍳 Egg toast")

            if "milk" in " ".join(food_names) and "cereal" in " ".join(food_names):
                if "milk" in " ".join(soon_foods):
                    suggestions.append("🥣 Cereal with milk — use the milk soon!")
                else:
                    suggestions.append("🥣 Cereal with milk")

            if "bread" in " ".join(food_names) and "cheese" in " ".join(food_names):
                if "cheese" in " ".join(soon_foods):
                    suggestions.append("🥪 Cheese sandwich — use the cheese soon!")
                else:
                    suggestions.append("🥪 Cheese sandwich")

            if not suggestions:
                suggestions.append("🍽️ Try combining the foods currently in your refrigerator.")


    return f"""
<!DOCTYPE html>

<html>

<head>

    <title>Smart Refrigerator</title>


    <style>

        body {{
            font-family: Arial, sans-serif;
            background: #dff3f8;
            margin: 0;
            padding: 25px;
            color: #123;
        }}

        h1 {{
            text-align: center;
            font-size: 36px;
            margin-bottom: 5px;
        }}

        .subtitle {{
            text-align: center;
            color: #52717a;
            font-size: 16px;
        }}

        .dashboard {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-top: 30px;
        }}

        .card {{
            background: white;
            padding: 20px;
            border-radius: 18px;
            text-align: center;
            box-shadow: 0 4px 12px #b8d5dc;
            border: 1px solid #c9e4e9;
        }}

        .value {{
            font-size: 28px;
            font-weight: bold;
            margin-top: 10px;
        }}

        .section {{
            background: white;
            margin-top: 25px;
            padding: 25px;
            border-radius: 18px;
            box-shadow: 0 4px 12px #b8d5dc;
        }}

        .food {{
            background: #eef8fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 12px;
            border-left: 5px solid #38a3b5;
        }}

        input {{
            padding: 12px;
            margin: 5px;
            border: 1px solid #b8d5dc;
            border-radius: 10px;
            font-size: 15px;
        }}

        button {{
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            background: #168aad;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }}

        button:hover {{
            background: #126f8a;
        }}

    </style>

</head>


<body>

    <h1>🧊 Smart Refrigerator</h1>

    <p class="subtitle">
        Intelligent Food & Temperature Management
    </p>


    <div class="dashboard">


        <div class="card">
           <h3>🌡️ Inside</h3>
           <p class="value" id="inside">{inside}°C</p>
        </div>
        



        <div class="card">
            <h3>☀️ Outside</h3>
            <p class="value" id="outside">{outside}°C</p>
        </div>


        <div class="card">
            <h3>💧 Humidity</h3>
            <p class="value" id="humidity">{humidity}%</p>
        </div>


        <div class="card">
            <h3>🚪 Door</h3>
            <p class="value" id="door">{door}</p>
        </div>


        <div class="card">
            <h3>❄️ Cooling</h3>
            <p class="value" id="cooling">
                ❄️ Cooling {cooling}%
            </p>
        </div>


    </div>


    <div class="section">
        <h2>📱 Add Food with QR</h2>

        <form action="/scan-qr" method="POST" enctype="multipart/form-data">
            <input
                type="file"
                name="qr"
                accept="image/*"
                required
            >

            <button type="submit">
                Scan QR Code
            </button>
        </form>
        
        <h2> Smart Refrigerator Status</h2>

        <div class="food">
            ✅ System Online<br>
            ❄️ Automatic Cooling Enabled<br>
            📱 QR Food Scanning Enabled<br>
            🔊 Voice Alerts Enabled<br>
            💾 Food Database Connected
        </div>
        <h2>📦 Food Inside</h2>

        {food_html}
        <h2>🍽️ Meal Suggestions</h2>

        <div class="food">
            {"<br>".join(suggestions)}
        </div>

    </div>


    <div class="section">

        <h2>➕ Add Food</h2>

        <form action="/add-food" method="POST">

            <input
                type="text"
                name="food"
                placeholder="Food name"
                required
            >

            <input
                type="date"
                name="expiry"
                required
            >

            <button type="submit">
                Add Food
            </button>

        </form>

    </div>


<script>
async function updateSensors() {{
    const response = await fetch("/api/sensors");
    const data = await response.json();

    document.getElementById("inside").textContent = data.inside + "°C";
    document.getElementById("outside").textContent = data.outside + "°C";
    document.getElementById("humidity").textContent = data.humidity + "%";
    document.getElementById("door").textContent = data.door;
    document.getElementById("cooling").textContent =
        data.cooling > 30
            ? "❄️ ACTIVE — " + data.cooling + "%"
            : "❄️ LOW — " + data.cooling + "%";
}}

updateSensors();
setInterval(updateSensors, 5000);
</script>    

</body>
</html>
"""


@app.route("/add-food", methods=["POST"])
def add_food():

    food_name = request.form["food"]
    expiry_date = request.form["expiry"]

    foods.append({
        "name": food_name,
        "expiry": expiry_date
    })
    connection = sqlite3.connect("refrigerator.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM foods WHERE name = ? AND expiry = ?",
        (food_name, expiry_date)
    )

    existing_food = cursor.fetchone()

    if existing_food:
        connection.close()
        return "⚠️ This food is already in the refrigerator."

    if not existing_food:
        cursor.execute(
            "INSERT INTO foods (name, expiry) VALUES (?, ?)",
            (food_name, expiry_date)
        )

    connection.commit()
    connection.close()

    return f"""
    <h2>✅ {food_name} added successfully!</h2>
    <a href="/">Back to Refrigerator</a>
    """

@app.route("/delete-food/<int:food_id>", methods=["POST"])
def delete_food(food_id):

    connection = sqlite3.connect("refrigerator.db")
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM foods WHERE id = ?",
        (food_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/scan-qr", methods=["POST"])
def scan_qr_route():

    file = request.files["qr"]
    file.save("qr_upload.png")

    data = scan_qr("qr_upload.png")

    if data == "No QR code detected":
        return "No QR code detected"

    try:
        food_name, expiry_date = [part.strip() for part in data.split("|", 1)]

        if not food_name or not expiry_date:
            return "Invalid QR format"

        date.fromisoformat(expiry_date)

    except ValueError:
        return "Invalid QR format"

    foods.append({
        "name": food_name,
        "expiry": expiry_date
    })
    connection = sqlite3.connect("refrigerator.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM foods WHERE name = ? AND expiry = ?",
        (food_name, expiry_date)
    )

    existing_food = cursor.fetchone()

    if existing_food:
        connection.close()
        return "⚠️ This food is already in the refrigerator."

    if not existing_food:
        cursor.execute(
            "INSERT INTO foods (name, expiry) VALUES (?, ?)",
            (food_name, expiry_date)
        )

    connection.commit()
    connection.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)