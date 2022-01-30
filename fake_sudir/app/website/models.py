import time
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)

    first_name = db.Column(db.String(40), unique=False)
    last_name = db.Column(db.String(40), unique=False)
    middle_name = db.Column(db.String(40), unique=False)

    mail = db.Column(db.String(40), unique=False)
    mobile = db.Column(db.String(40), unique=False)

    telegram_code = db.relationship("TelegramCode", back_populates="user", uselist=False)

    def __str__(self):
        return self.username

    def get_user_id(self):
        return self.id

    def check_password(self, password):
        return password == 'valid'


class OAuth2Client(db.Model, OAuth2ClientMixin):
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

    def check_redirect_uri(self, redirect_uri):
        return True


class OAuth2AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'oauth2_code'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')


class OAuth2Token(db.Model, OAuth2TokenMixin):
    __tablename__ = 'oauth2_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

    def is_refresh_token_active(self):
        if self.revoked:
            return False
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at >= time.time()


class TelegramCode(db.Model):
    __tablename__ = 'telegram_code'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

    code = db.Column(db.String(6), unique=False)
    checked = db.Column(db.Boolean, unique=False)

    issued_at = db.Column(db.DateTime, unique=False)
    expires_at = db.Column(db.DateTime, unique=False)
    reissue_available_at = db.Column(db.DateTime, unique=False)
