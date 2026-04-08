import os

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Hospital, EmergencyRequest


def get_database_url():
    database_url = os.environ.get("DATABASE_URL", "sqlite:///ems.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def seed_demo_data():
    if not User.query.filter_by(username="admin").first():
        admin = User(full_name="System Admin", username="admin", role="admin", password_hash="x")
        admin.set_password("admin123")
        db.session.add(admin)

    if Hospital.query.count() == 0:
        hospitals = [
            Hospital(name="Al Shifa Hospital", location="Gaza City", available_beds=10, status="Open"),
            Hospital(name="European Gaza Hospital", location="Khan Younis", available_beds=3, status="Overloaded"),
            Hospital(name="Indonesian Hospital", location="North Gaza", available_beds=0, status="Unavailable"),
        ]
        db.session.add_all(hospitals)

    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "student-project-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---------- Helpers ----------
    def require_role(*roles):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if current_user.role not in roles:
            abort(403)
        return None

    # ---------- Public / Citizen ----------
    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/hospitals")
    def hospitals():
        hospitals = Hospital.query.order_by(Hospital.name.asc()).all()
        return render_template("hospitals.html", hospitals=hospitals)

    @app.route("/submit", methods=["GET", "POST"])
    @login_required
    def submit_request():
        # Only citizens can submit requests
        role_check = require_role("citizen")
        if role_check:
            return role_check

        hospitals = Hospital.query.order_by(Hospital.name.asc()).all()

        if request.method == "POST":
            emergency_type = request.form.get("emergency_type", "").strip()
            location = request.form.get("location", "").strip()
            description = request.form.get("description", "").strip()
            hospital_id_raw = request.form.get("hospital_id", "").strip()

            if not emergency_type or not location or not hospital_id_raw:
                flash("Emergency type, location, and hospital are required.", "danger")
                return redirect(url_for("submit_request"))

            try:
                hospital_id = int(hospital_id_raw)
            except ValueError:
                flash("Invalid hospital selected.", "danger")
                return redirect(url_for("submit_request"))

            hospital = Hospital.query.get(hospital_id)
            if not hospital:
                flash("Selected hospital was not found.", "danger")
                return redirect(url_for("submit_request"))

            new_req = EmergencyRequest(
                emergency_type=emergency_type,
                location=location,
                description=description or None,
                citizen_id=current_user.id,
                hospital_id=hospital.id,
                status="Pending"
            )
            db.session.add(new_req)
            db.session.commit()

            flash(f"Request submitted to {hospital.name}.", "success")

            return redirect(url_for("my_requests"))

        return render_template("submit_request.html", hospitals=hospitals)

    @app.route("/my-requests")
    @login_required
    def my_requests():
        role_check = require_role("citizen")
        if role_check:
            return role_check

        requests_list = EmergencyRequest.query.filter_by(citizen_id=current_user.id)\
            .order_by(EmergencyRequest.created_at.desc()).all()
        return render_template("my_requests.html", requests_list=requests_list)

    @app.route("/cancel/<int:req_id>", methods=["POST"])
    @login_required
    def cancel_request(req_id):
        role_check = require_role("citizen")
        if role_check:
            return role_check

        req_obj = EmergencyRequest.query.get_or_404(req_id)
        if req_obj.citizen_id != current_user.id:
            abort(403)

        if req_obj.status in ["Accepted", "Rejected"]:
            flash("You cannot cancel a request after it is accepted/rejected.", "danger")
            return redirect(url_for("my_requests"))

        req_obj.status = "Cancelled"
        db.session.commit()
        flash("Request cancelled.", "success")
        return redirect(url_for("my_requests"))

    # ---------- Auth ----------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                flash("Logged in successfully.", "success")
                if user.role == "admin":
                    return redirect(url_for("admin_dashboard"))
                if user.role == "staff":
                    return redirect(url_for("staff_dashboard"))
                return redirect(url_for("home"))

            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if not full_name or not username or not password:
                flash("All fields are required.", "danger")
                return redirect(url_for("signup"))

            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "danger")
                return redirect(url_for("signup"))

            user = User(
                full_name=full_name,
                username=username,
                role="citizen",
                password_hash="x"
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Account created successfully. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("signup.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("home"))

    # ---------- Staff ----------
    @app.route("/staff")
    @login_required
    def staff_dashboard():
        role_check = require_role("staff")
        if role_check:
            return role_check

        if not current_user.hospital_id:
            flash("Staff account is not linked to a hospital. Contact admin.", "danger")
            return render_template("staff_dashboard.html", hospital=None, requests_list=[])

        hospital = Hospital.query.get(current_user.hospital_id)
        requests_list = EmergencyRequest.query.filter_by(hospital_id=hospital.id)\
            .order_by(EmergencyRequest.created_at.desc()).all()

        return render_template("staff_dashboard.html", hospital=hospital, requests_list=requests_list)

    @app.route("/staff/update-hospital", methods=["POST"])
    @login_required
    def staff_update_hospital():
        role_check = require_role("staff")
        if role_check:
            return role_check

        if not current_user.hospital_id:
            abort(400)

        hospital = Hospital.query.get_or_404(current_user.hospital_id)
        status = request.form.get("status", "Open")
        beds_raw = request.form.get("available_beds", "0")

        try:
            beds = int(beds_raw)
            if beds < 0:
                beds = 0
        except ValueError:
            beds = hospital.available_beds

        if status not in ["Open", "Overloaded", "Unavailable"]:
            status = "Open"

        hospital.status = status
        hospital.available_beds = beds
        db.session.commit()

        flash("Hospital status updated.", "success")
        return redirect(url_for("staff_dashboard"))

    @app.route("/staff/request/<int:req_id>/set", methods=["POST"])
    @login_required
    def staff_set_request_status(req_id):
        role_check = require_role("staff")
        if role_check:
            return role_check

        new_status = request.form.get("status", "").strip()
        if new_status not in ["Accepted", "Rejected"]:
            abort(400)

        req_obj = EmergencyRequest.query.get_or_404(req_id)

        # Ensure staff only edits requests for their hospital
        if req_obj.hospital_id != current_user.hospital_id:
            abort(403)

        # Don’t change cancelled requests
        if req_obj.status == "Cancelled":
            flash("Cannot update a cancelled request.", "danger")
            return redirect(url_for("staff_dashboard"))

        hospital = Hospital.query.get(req_obj.hospital_id)

        if new_status == "Accepted":
            if hospital.available_beds <= 0:
                flash("No available beds. Cannot accept request.", "danger")
                return redirect(url_for("staff_dashboard"))

            hospital.available_beds -= 1
            req_obj.status = "Accepted"

            # OPTIONAL but recommended
            if hospital.available_beds == 0:
                hospital.status = "Overloaded"

        elif new_status == "Rejected":
            req_obj.status = "Rejected"

        db.session.commit()

        flash(f"Request #{req_obj.id} marked as {new_status}.", "success")
        return redirect(url_for("staff_dashboard"))

    # ---------- Admin ----------
    @app.route("/admin")
    @login_required
    def admin_dashboard():
        role_check = require_role("admin")
        if role_check:
            return role_check

        stats = {
            "hospitals": Hospital.query.count(),
            "users": User.query.count(),
            "requests": EmergencyRequest.query.count(),
            "pending": EmergencyRequest.query.filter_by(status="Pending").count(),
        }
        latest_requests = EmergencyRequest.query.order_by(EmergencyRequest.created_at.desc()).limit(10).all()
        return render_template("admin_dashboard.html", stats=stats, latest_requests=latest_requests)

    @app.route("/admin/hospitals", methods=["GET", "POST"])
    @login_required
    def admin_hospitals():
        role_check = require_role("admin")
        if role_check:
            return role_check

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            location = request.form.get("location", "").strip()
            beds_raw = request.form.get("available_beds", "0").strip()
            status = request.form.get("status", "Open").strip()

            if not name or not location:
                flash("Name and location are required.", "danger")
                return redirect(url_for("admin_hospitals"))

            try:
                beds = int(beds_raw)
                if beds < 0:
                    beds = 0
            except ValueError:
                beds = 0

            if status not in ["Open", "Overloaded", "Unavailable"]:
                status = "Open"

            h = Hospital(name=name, location=location, available_beds=beds, status=status)
            db.session.add(h)
            db.session.commit()
            flash("Hospital added.", "success")
            return redirect(url_for("admin_hospitals"))

        hospitals = Hospital.query.order_by(Hospital.name.asc()).all()
        return render_template("admin_hospitals.html", hospitals=hospitals)

    @app.route("/admin/create-staff", methods=["GET", "POST"])
    @login_required
    def admin_create_staff():
        role_check = require_role("admin")
        if role_check:
            return role_check

        hospitals = Hospital.query.order_by(Hospital.name.asc()).all()

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            hospital_id_raw = request.form.get("hospital_id", "").strip()

            if not full_name or not username or not password or not hospital_id_raw:
                flash("All fields are required.", "danger")
                return redirect(url_for("admin_create_staff"))

            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "danger")
                return redirect(url_for("admin_create_staff"))

            try:
                hospital_id = int(hospital_id_raw)
            except ValueError:
                flash("Invalid hospital.", "danger")
                return redirect(url_for("admin_create_staff"))

            if not Hospital.query.get(hospital_id):
                flash("Hospital not found.", "danger")
                return redirect(url_for("admin_create_staff"))

            u = User(full_name=full_name, username=username, role="staff", hospital_id=hospital_id, password_hash="x")
            u.set_password(password)
            db.session.add(u)
            db.session.commit()

            flash("Staff account created.", "success")
            return redirect(url_for("admin_create_staff"))

        return render_template("admin_create_staff.html", hospitals=hospitals)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("base.html", content_only="403 Forbidden"), 403

    return app

app = create_app()

with app.app_context():
    db.create_all()
    seed_demo_data()

if __name__ == "__main__":
    app.run(debug=True)
