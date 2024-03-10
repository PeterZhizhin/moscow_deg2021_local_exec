import os
from website.app import create_app

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "sqlite:///" + os.path.join(os.getcwd(), "database", "db.sqlite"),
)

app = create_app(
    {
        "SECRET_KEY": "secret",
        "OAUTH2_REFRESH_TOKEN_GENERATOR": True,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_DATABASE_URI": SQLALCHEMY_DATABASE_URI,
    }
)
