import os
import time
import logging
import sqlalchemy.exc
from flask import Flask
from .models import db, User, OAuth2Client
from .oauth2 import config_oauth
from .routes import bp


def create_db_elements():
    if User.query.count() > 0:
        return
    admin_user = User(
        username="admin",
        first_name="admin_first",
        last_name="admin_last",
        middle_name="admin_middle",
        mail="admin_mail",
        mobile="admin_mobile",
    )
    db.session.add(admin_user)
    db.session.commit()

    client = OAuth2Client(
        client_id="deg_client_id",
        client_secret="deg_client_secret",
        client_id_issued_at=int(time.time()),
        user_id=admin_user.id,
    )
    client.set_client_metadata(
        {
            "client_name": "deg_client",
            "client_uri": "http://deg_client_uri",
            "grant_types": ["authorization_code"],
            "redirect_uris": ["http://localhost/fake_redirect_uri"],
            "response_types": ["code"],
            "scope": "openid profile contacts",
            "token_endpoint_auth_method": "client_secret_post",
        }
    )
    db.session.add(client)
    db.session.commit()


def create_app(config=None):
    app = Flask(__name__)

    # load default configuration
    app.config.from_object("website.settings")

    # load environment configuration
    if "WEBSITE_CONF" in os.environ:
        app.config.from_envvar("WEBSITE_CONF")

    # load app specified configuration
    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith(".py"):
            app.config.from_pyfile(config)

    setup_app(app)
    return app


def setup_app(app):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )

    db.init_app(app)

    # Create tables if they do not exist already
    with app.app_context():
        # Uncomment the next line for clean start.
        # db.drop_all()

        while True:
            wait_start = time.time()
            try:
                db.create_all()
                break
            except sqlalchemy.exc.OperationalError as e:
                app.logger.error(f"Database creation failed: {e}")
                current_time = time.time()
                if current_time - wait_start > 60:
                    raise RuntimeError("Database creation failed in 60 seconds") from e
                time.sleep(4)

        create_db_elements()
    config_oauth(app)
    app.register_blueprint(bp, url_prefix="")
