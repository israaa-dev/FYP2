from app import app
from models import db, User, Hospital

def run():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            admin = User(full_name="System Admin", username="admin", role="admin", password_hash="x")
            admin.set_password("admin123")
            db.session.add(admin)

        if Hospital.query.count() == 0:
            h1 = Hospital(name="Al Shifa Hospital", location="Gaza City", available_beds=10, status="Open")
            h2 = Hospital(name="European Gaza Hospital", location="Khan Younis", available_beds=3, status="Overloaded")
            h3 = Hospital(name="Indonesian Hospital", location="North Gaza", available_beds=0, status="Unavailable")
            db.session.add_all([h1, h2, h3])

        db.session.commit()
        print("Seed complete.")
        print("ADMIN:    admin / admin123")
        print("Now create STAFF from Admin panel after login.")

if __name__ == "__main__":
    run()
