import os
import uuid
import datetime
from flask import Flask, render_template, request, redirect, flash, session, jsonify
from services.dynamodb_service import (
    create_user, get_user, create_booking, get_user_bookings,
    cancel_booking, get_booking
)
from services.sns_service import send_notification
from data import TRANSPORT_DATA, HOTEL_DATA

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'travelgo_secret_2024')

# Inject session into every template context automatically
@app.context_processor
def inject_session():
    return dict(session=session)

# ── Helper: always pass logged_in state to every template ──
def render(template, **kwargs):
    kwargs.setdefault('logged_in', 'user_email' in session)
    kwargs.setdefault('user_name', session.get('user_name', ''))
    return render_template(template, **kwargs)

# ─────────────── HOME ───────────────
@app.route("/")
def home():
    return render("index.html")

# ─────────────── ABOUT ───────────────
@app.route("/about")
def about():
    return render("about.html")

# ─────────────── REGISTER ───────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if 'user_email' in session:
        return redirect("/dashboard")

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        mobile   = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not all([name, email, mobile, password]):
            flash("All fields are required.", "error")
            return render("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render("register.html")

        try:
            existing = get_user(email)
            if existing:
                flash("An account with this email already exists.", "error")
                return render("register.html")

            user_id = str(uuid.uuid4())
            user = {
                "user_id": user_id,
                "name": name,
                "email": email,
                "mobile": mobile,
                "password": password,
                "created_at": datetime.datetime.now().isoformat()
            }
            create_user(user)

            # SNS – non-blocking
            try:
                send_notification(
                    email,
                    f"Welcome to TravelGo, {name}!\n\nYour account has been created.\nEmail: {email}\n\nStart exploring!\n\n– TravelGo Team",
                    "Welcome to TravelGo!"
                )
            except Exception as sns_err:
                print(f"[SNS] Registration notification skipped: {sns_err}")

            flash("Account created successfully! Please login.", "success")
            return redirect("/login")

        except Exception as e:
            flash(f"Registration failed: {str(e)}", "error")
            return render("register.html")

    return render("register.html")

# ─────────────── LOGIN ───────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_email' in session:
        return redirect("/dashboard")

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            user = get_user(email)
            if user and user.get("password") == password:
                session['user_email'] = email
                session['user_name']  = user.get("name", "Traveller")
                session['user_id']    = user.get("user_id", "")
                flash(f"Welcome back, {user.get('name', 'Traveller')}! Ready to explore?", "success")
                return redirect("/dashboard")
            else:
                flash("Invalid email or password.", "error")
        except Exception as e:
            flash(f"Login error: {str(e)}", "error")

    return render("login.html")

# ─────────────── LOGOUT ───────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out. Safe travels!", "success")
    return redirect("/")

# ─────────────── DASHBOARD ───────────────
@app.route("/dashboard")
def dashboard():
    if 'user_email' not in session:
        flash("Please login to access your dashboard.", "error")
        return redirect("/login")
    try:
        bookings = get_user_bookings(session['user_email'])
    except Exception as e:
        print(f"[DB] Could not fetch bookings: {e}")
        bookings = []
    return render("dashboard.html",
                  user_email=session.get('user_email'),
                  bookings=bookings)

# ─────────────── MY ORDERS ───────────────
@app.route("/my_orders")
def my_orders():
    if 'user_email' not in session:
        flash("Please login to view your orders.", "error")
        return redirect("/login")
    try:
        bookings = get_user_bookings(session['user_email'])
    except Exception as e:
        print(f"[DB] Could not fetch bookings: {e}")
        bookings = []
    return render("my_orders.html", bookings=bookings)

# ─────────────── SEARCH ───────────────
@app.route("/search", methods=["GET", "POST"])
def search():
    if 'user_email' not in session:
        flash("Please login to search for trips.", "error")
        return redirect("/login")

    mode        = request.form.get("mode") or request.args.get("mode", "flight")
    source      = (request.form.get("source") or request.args.get("source", "")).strip().lower()
    destination = (request.form.get("destination") or request.args.get("destination", "")).strip().lower()
    travel_date = request.form.get("date") or request.args.get("date", "")
    city        = (request.form.get("city") or request.args.get("city", "")).strip().lower()
    passengers  = request.form.get("passengers") or request.args.get("passengers", "1")

    results = []
    if mode in ["flight", "train", "bus"]:
        for item in TRANSPORT_DATA.get(mode, []):
            if source and destination:
                if item["source"].lower() == source and item["destination"].lower() == destination:
                    results.append(item)
            else:
                results.append(item)
    elif mode == "hotel":
        for item in HOTEL_DATA:
            if city:
                if item["location"].lower() == city:
                    results.append(item)
            else:
                results.append(item)

    return render("search_results.html",
                  mode=mode, source=source, destination=destination,
                  travel_date=travel_date, city=city,
                  passengers=passengers, results=results)

# ─────────────── CHECKOUT ───────────────
@app.route("/checkout", methods=["POST"])
def checkout():
    if 'user_email' not in session:
        flash("Please login to book.", "error")
        return redirect("/login")

    mode       = request.form.get("mode", "flight")
    item_id    = request.form.get("item_id", "")
    travel_date = request.form.get("date", "")
    passengers  = request.form.get("passengers", "1")

    item = None
    if mode in ["flight", "train", "bus"]:
        for t in TRANSPORT_DATA.get(mode, []):
            if t["id"] == item_id:
                item = t
                break
    elif mode == "hotel":
        for h in HOTEL_DATA:
            if h["id"] == item_id:
                item = h
                break

    if not item:
        flash("Selected item not found. Please search again.", "error")
        return redirect("/search?mode=" + mode)

    # Store in session so confirm_booking can read it
    session['checkout'] = {
        "mode": mode,
        "item_id": item_id,
        "item": item,
        "date": travel_date,
        "passengers": passengers
    }

    return render("checkout.html", mode=mode, item=item,
                  date=travel_date, passengers=passengers)

# ─────────────── CONFIRM BOOKING ───────────────
@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():
    if 'user_email' not in session:
        flash("Session expired. Please login again.", "error")
        return redirect("/login")

    co          = session.get('checkout', {})
    mode        = co.get("mode", "flight")
    item        = co.get("item", {})
    travel_date = co.get("date", "")
    passengers  = int(co.get("passengers", 1))

    if not item:
        flash("Booking session expired. Please start again.", "error")
        return redirect("/search")

    email     = session['user_email']
    user_name = session.get('user_name', '')
    user_id   = session.get('user_id', '')

    booking_id    = "TRV" + str(uuid.uuid4())[:8].upper()
    cost_per_unit = float(item.get("cost", 0))

    if mode == "hotel":
        nights     = int(request.form.get("nights", 1))
        total_cost = cost_per_unit * nights
        details    = f"{item.get('name')} – {nights} night(s)"
        type_id    = ""
        hotel_id   = item.get("id", "")
    else:
        nights     = 0
        total_cost = cost_per_unit * passengers
        details    = f"{item.get('source','').title()} → {item.get('destination','').title()} ({passengers} passenger(s))"
        type_id    = item.get("id", "")
        hotel_id   = ""

    # Build booking – NO None values (DynamoDB rejects null)
    booking_data = {
        "booking_id":  booking_id,
        "user_id":     user_id,
        "user_email":  email,
        "mode":        mode,
        "type_id":     type_id,
        "hotel_id":    hotel_id,
        "item_name":   item.get("name", item.get("source", "")),
        "details":     details,
        "travel_date": travel_date or "",
        "passengers":  str(passengers),
        "total_cost":  str(int(total_cost)),
        "status":      "confirmed",
        "book_date":   datetime.datetime.now().isoformat()
    }

    try:
        create_booking(booking_data)
    except Exception as e:
        flash(f"Booking failed: {str(e)}", "error")
        return redirect("/dashboard")

    session.pop('checkout', None)

    # SNS – non-blocking
    try:
        send_notification(
            email,
            f"Hi {user_name}!\n\nBooking CONFIRMED!\n\nID: {booking_id}\nType: {mode.title()}\nDetails: {details}\nDate: {travel_date}\nTotal: Rs.{int(total_cost)}\n\nHave a wonderful journey!\n– TravelGo Team",
            f"TravelGo Booking Confirmed – {booking_id}"
        )
    except Exception as e:
        print(f"[SNS] Booking notification skipped: {e}")

    return render("ticket.html", booking=booking_data)

# ─────────────── CANCEL BOOKING ───────────────
@app.route("/cancel_booking", methods=["POST"])
def cancel_booking_route():
    if 'user_email' not in session:
        flash("Please login to manage bookings.", "error")
        return redirect("/login")

    booking_id = request.form.get("booking_id", "")
    email      = session['user_email']
    user_name  = session.get('user_name', '')

    try:
        cancel_booking(booking_id, email)
        flash(f"Booking {booking_id} has been cancelled.", "success")
        try:
            send_notification(
                email,
                f"Hi {user_name},\n\nYour booking {booking_id} has been cancelled.\n\n– TravelGo Team",
                f"TravelGo Booking Cancelled – {booking_id}"
            )
        except Exception as e:
            print(f"[SNS] Cancellation notification skipped: {e}")
    except Exception as e:
        flash(f"Cancellation failed: {str(e)}", "error")

    return redirect("/my_orders")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
