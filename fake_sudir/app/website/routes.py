from datetime import datetime, timedelta
import logging
import time
import json
import random
import uuid
import urllib.parse
from functools import wraps
import hmac
import hashlib
import os
import string
import secrets
from typing import Dict, List


from flask import Blueprint, request, session, url_for, abort, make_response
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error

import telegram
from telegram.error import NetworkError, Unauthorized

from .models import db, User, OAuth2Client, TelegramCode
from .oauth2 import authorization, require_oauth

TELEGRAM_CODE_EXPIRES_IN = timedelta(minutes=1)
TELEGRAM_CODE_REISSUE_IN = timedelta(seconds=30)
USER_KEYS = ["id", "first_name", "last_name", "middle_name", "mobile", "mail"]

logger = logging.getLogger(__name__)

bp = Blueprint("home", __name__)


def current_user():
    if "id" in session:
        uid = session["id"]
        return User.query.get(uid)
    return None


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


def generate_code():
    return "".join(secrets.choice(string.digits) for _ in range(6))


def create_telegram_code():
    code = TelegramCode()
    code.issued_at = datetime.now()
    code.expires_at = code.issued_at + TELEGRAM_CODE_EXPIRES_IN
    code.reissue_available_at = code.issued_at + TELEGRAM_CODE_REISSUE_IN
    code.code = generate_code()
    return code


def maybe_send_code(user: User) -> None:
    if user.telegram_code is not None:
        if datetime.now() < user.telegram_code.reissue_available_at:
            abort(400, "Code reissue is not available yet")
        db.session.delete(user.telegram_code)
    user.telegram_code = create_telegram_code()
    db.session.add(user.telegram_code)
    db.session.commit()

    bot = telegram.Bot(os.environ.get("TELEGRAM_BOT_TOKEN"))
    code = user.telegram_code.code
    bot.send_message(
        chat_id=user.id,
        text=f"Your code for authorization at fake SUDIR: {code}",
    )


def validate_code_is_correct(user: User, entered_code: str) -> None:
    if user.telegram_code is None:
        abort(400, "No code has been issued")
    if user.telegram_code.checked:
        abort(401, "Code has already been checked, wait and try to login again")
    if user.telegram_code.expires_at < datetime.now():
        abort(401, "Code is expired, try to login again")

    logger.debug(f"Entered {entered_code}, correct {user.telegram_code.code}")
    ok = user.telegram_code.code == entered_code
    user.telegram_code.checked = True
    db.session.commit()
    if not ok:
        abort(401, "Wrong code")


@bp.route("/oauth/register", methods=("GET", "POST"))
def home():
    if request.method == "POST":
        mobile = request.form.get("mobile")
        mobile = mobile.replace("-", "").replace("+", "")
        user = User.query.filter_by(mobile=mobile).first()
        if not user:
            abort(
                404,
                "No such user, please register via the telegram bot: t.me/TestDeg123_bot",
            )

        maybe_send_code(user)

        next_page = request.args.get("next") or "/"
        return redirect(url_for(".enter_tg_code", next=next_page, mobile=user.mobile))
    else:
        user = current_user()
        if user:
            clients = OAuth2Client.query.filter_by(user_id=user.id).all()
        else:
            clients = []

        return render_template("home.html", user=user, clients=clients)


@bp.route("/oauth/enter_tg_code", methods=("GET", "POST"))
def enter_tg_code():
    if request.method == "GET":
        username = request.args.get("mobile")
        user = User.query.filter_by(username=username).first()
        if not user:
            abort(400)
        return render_template("enter_tg_code.html", user=user)
    else:
        username = request.args.get("mobile")

        user = User.query.filter_by(username=username).first()
        if not user:
            abort(400)
        entered_code = request.form.get("tg_code")

        validate_code_is_correct(user, entered_code)

        logger.debug(f"Telegram code is correct, logging {user.username} in")
        session["id"] = user.id

        next_page = request.args.get("next", "/")
        return redirect(next_page)


@bp.route("/oauth/logout")
def logout():
    del session["id"]
    return redirect("/election")


@bp.route("/create_client", methods=("GET", "POST"))
def create_client(user=None):
    user = current_user()
    if not user:
        return redirect("/")
    if request.method == "GET":
        return render_template("create_client.html")

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = OAuth2Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        user_id=user.id,
    )

    form = request.form
    client_metadata = {
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": split_by_crlf(form["grant_type"]),
        "redirect_uris": split_by_crlf(form["redirect_uri"]),
        "response_types": split_by_crlf(form["response_type"]),
        "scope": form["scope"],
        "token_endpoint_auth_method": form["token_endpoint_auth_method"],
    }
    client.set_client_metadata(client_metadata)

    if form["token_endpoint_auth_method"] == "none":
        client.client_secret = ""
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()

    return redirect("/")


# def canonize_dict(d: Dict, keys: List[str]) -> str:
#     return json.dumps([d.get(key) for key in keys])


# def validate_bot(data: Dict, keys: List[str]) -> None:
#     key = os.environ.get("TELEGRAM_BOT_SECRET").encode()
#     canonized = canonize_dict(data, keys)
#     h = hmac.new(key, canonized.encode(), hashlib.sha256)
#     logger.debug(f"Canonized: {canonized.encode()}, digest: {h.hexdigest()}")
#     if not secrets.compare_digest(data["auth_hmac"], h.hexdigest()):
#         abort(401)


def validate_bot(token: str) -> None:
    correct_token = os.environ.get("TELEGRAM_BOT_SECRET")
    if not isinstance(token, str):
        abort(400, "Token must be string")
    if not secrets.compare_digest(token, correct_token):
        abort(401)


def _create_fake_phone_number() -> str:
    while True:
        mobile_int = random.randrange(10**10)
        mobile_str = f"7{mobile_int:010}"

        if User.query.filter_by(mobile=mobile_str).first():
            continue

        return mobile_str


def _fake_string() -> str:
    return "".join(random.choice(string.ascii_letters) for _ in range(30))


@bp.route("/oauth/tg/redirect_to_vote")
def redirect_to_vote():
    token = request.args.get("token")

    user = User.query.filter_by(telegram_validate_token=token).first()
    if not user:
        abort(400, "No user with such token")

    session["id"] = user.id
    return authorization.create_authorization_response(grant_user=user)


@bp.route("/oauth/tg/register", methods=["POST"])
def tg_register():
    # validate_bot(request.form, USER_KEYS)
    validate_bot(request.form.get("token"))

    telegram_id = request.form.get("id")
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if user:
        return ("Вы уже зарегистрированы на голосование", 400)

    user_id = random.getrandbits(62)
    mobile = _create_fake_phone_number()
    username = _fake_string()
    mail = f"{mobile}@telegram.org"
    first_name = _fake_string()
    last_name = _fake_string()
    middle_name = _fake_string()
    telegram_validate_token = str(uuid.uuid4())

    logger.info(
        f"Registering user id={user_id}, username={username}, telegram_id={telegram_id}"
    )
    user = User(
        id=user_id,
        telegram_id=telegram_id,
        telegram_validate_token=telegram_validate_token,
        username=username,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        mail=mail,
        mobile=mobile,
    )
    db.session.add(user)
    db.session.commit()

    sudir_tg_redirect_url = os.environ.get(
        "SUDIR_TG_REDIRECT_URL",
        "http://localhost",
    )

    redirect_to_vote_url = os.environ.get(
        "SUDIR_REDIRECT_TO_VOTE_URL",
        "http://localhost/got_authorize",
    )
    redirect_override_request_uri = os.environ.get(
        "SUDIR_REDIRECT_OVERRIDE_REQUEST_URI",
        "/election",
    )

    redirect_to_vote_url_params = urllib.parse.urlencode(
        {
            "request_uri_override": redirect_override_request_uri,
        }
    )
    redirect_to_vote_url_with_params = (
        f"{redirect_to_vote_url}?{redirect_to_vote_url_params}"
    )

    redirect_url = urllib.parse.urljoin(
        sudir_tg_redirect_url, "/oauth/tg/redirect_to_vote"
    )
    params = urllib.parse.urlencode(
        {
            "token": telegram_validate_token,
            "redirect_uri": redirect_to_vote_url_with_params,
            "response_type": "code",
            "client_id": "deg_client_id",
            "scope": "openid+profile+contacts",
        }
    )
    redirect_url_with_params = f"{redirect_url}?{params}"

    return (
        json.dumps(
            {
                "success": True,
                "user_id": user_id,
                "mobile": mobile,
                "redirect_url": redirect_url_with_params,
            }
        ),
        200,
        {"ContentType": "application/json"},
    )


@bp.route("/oauth/tg/send_message", methods=["POST"])
def tg_send_message():
    params = request.json
    logger.debug(f"request: {params}")
    validate_bot(params.get("token"))

    mobile = params.get("destination")
    user = User.query.filter_by(mobile=mobile).first()
    if not user:
        logger.warning(f"User {mobile} not found")
        abort(404, f"User {mobile} not found")

    bot = telegram.Bot(os.environ.get("TELEGRAM_BOT_TOKEN"))
    message = params.get("message")
    logger.debug(f"Sending message to user {user.mobile}: {message}")
    bot.send_message(
        chat_id=user.telegram_id,
        text=message,
    )


@bp.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    user = current_user()
    # if user log status is not true (Auth server), then to log it in
    if not user:
        return redirect(url_for(".home", next=request.url))

    return authorization.create_authorization_response(grant_user=user)


@bp.route("/oauth/token", methods=["POST"])
def issue_token():
    return authorization.create_token_response()


@bp.route("/oauth/revoke", methods=["POST"])
def revoke_token():
    return authorization.create_endpoint_response("revocation")


@bp.route("/api/me")
@require_oauth("profile")
def api_me():
    user = current_token.user
    return dict(
        guid=user.id,
        FirstName=user.first_name,
        LastName=user.last_name,
        MiddleName=user.middle_name,
        mail=user.mail,
        mobile=user.mobile,
        trusted=True,
        username=user.username,
    )
