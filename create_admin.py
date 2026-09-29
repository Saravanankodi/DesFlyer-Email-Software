from app import app
from models import db
from models.user import User


with app.app_context():

    existing_user = User.query.filter_by(
        email="admin@desflyer.com"
    ).first()


    if existing_user:

        print("Admin user already exists.")

    else:

        user = User(
            name="DesFlyer Admin",
            email="admin@desflyer.com"
        )

        user.set_password("Admin@123")

        db.session.add(user)

        db.session.commit()

        print("Admin user created successfully.")