import time
import secrets

from flask import Flask, request
from functools import wraps

from hashlib import blake2b, sha256

app = Flask(__name__)
app.config.from_object("config")


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if "x-application-token" not in request.headers:
            return {"errorCode": 1, "errorMessage": "No token was provided"}
        token = request.headers["x-application-token"]
        if token != app.config["MDM_GID_SERVICE_TOKEN"]:
            return {"errorCode": 2, "errorMessage": "Wrong token was provided to MDM"}
        return f(*args, **kwargs)

    return decorator


@app.route("/generate_gid", methods=["POST"])
@token_required
def generate_gid():
    print("Got request: {}".format(request.json))
    print("Request headers: {}".format(request.headers))
    ssoId = request.json.get("ssoId")
    if ssoId is None:
        return {"errorCode": "3", "errorMessage": "Missing ssoId from request"}

    secret = app.config["SECRET_KEY"]
    hash_func = blake2b(key=bytes.fromhex(app.config["SECRET_KEY"]))
    hash_func.update(ssoId.encode("utf-8"))

    hash_value = hash_func.hexdigest()

    return {"externalId": hash_value}


def get_sha_signature():
    timestamp = int(time.time() * 1000)
    random_val = secrets.token_hex(32)
    secret = app.config["SIGN_SECRET"]

    for_sign_string = "{}|{}|{}".format(timestamp, random_val, secret).encode("utf-8")
    h = sha256()
    h.update(for_sign_string)
    resulting_hash = h.hexdigest()
    return {
        "random": random_val,
        "timestamp": timestamp,
        "secureHash": resulting_hash,
    }


def get_response(return_code):
    signature = get_sha_signature()
    signature["externalId"] = secrets.token_hex(16)
    signature["district"] = {"districtNumber": app.config["DISTRICT"]}
    signature["code"] = [return_code]
    return signature


# These two methods are just to have a fake election with no voters in fake_arm response.
@app.route("/failing/checkBallot", methods=["POST"])
def check_ballot_fail():
    return {"code": app.config["USER_HAS_NO_ACCESS_CODE"]}


@app.route("/failing/getBallot", methods=["POST"])
def get_ballot_fail():
    return {"code": app.config["USER_HAS_NO_ACCESS_CODE"]}


@app.route("/checkBallot", methods=["POST"])
@token_required
def check_ballot():
    print("Got request: {}".format(request.json))
    print("Request headers: {}".format(request.headers))

    ssoId = request.json.get("ssoId")
    if ssoId is None:
        return {"errorCode": "3", "errorMessage": "Missing ssoId from request"}

    result = get_response(app.config["CHECK_BALLOT_SUCCESS_CODE"])

    print("Returning {}".format(result))
    return result


@app.route("/getBallot", methods=["POST"])
@token_required
def get_ballot():
    print("Got request: {}".format(request.json))
    print("Request headers: {}".format(request.headers))

    ssoId = request.json.get("ssoId")
    if ssoId is None:
        return {"errorCode": "3", "errorMessage": "Missing ssoId from request"}

    result = get_response(app.config["GET_BALLOT_SUCCESS_CODE"])

    print("Returning {}".format(result))
    return result


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
