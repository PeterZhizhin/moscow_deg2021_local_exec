import dataclasses
from typing import Any

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, url_for
import sqlalchemy.exc
import time

import requests

import collections
import copy
import json
import logging
import os
import random
import traceback
import urllib.parse

app = Flask(__name__)
app.config.from_object("config")
app.logger.setLevel(logging.INFO)

db = SQLAlchemy(app)


def _refresh_deg_caches():
    urls = app.config["REFRESH_CACHE_URLS"].split(";")
    system = app.config["REFRESH_CACHE_SYSTEM"]
    token = app.config["REFRESH_CACHE_TOKEN"]
    for url in urls:
        app.logger.info(f"Refreshing cache for URL: {url}")
        try:
            requests.get(url, headers={"SYSTEM": system, "SYSTEM_TOKEN": token})
        except requests.exceptions.HTTPError as err:
            app.logger.error(
                f"Got error when trying to refresh URL {url}: {err} {err.response.text}"
            )


def _generate_candidate_id(existing_ids=None):
    if existing_ids is None:
        return random.randrange(2**32)
    x = _generate_candidate_id()
    while x in existing_ids:
        x = _generate_candidate_id()
    return x


def _generate_candidate_ids(n) -> list[int]:
    existing_ids = set()
    candidate_ids = []
    for _ in range(n):
        candidate_id = _generate_candidate_id(existing_ids)
        candidate_ids.append(candidate_id)
        existing_ids.add(candidate_id)

    candidate_ids.sort()
    return candidate_ids


class Voting(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)
    external_voting_id = db.Column(db.String, nullable=False)
    public_key = db.Column(db.String, nullable=False)
    is_running = db.Column(db.Boolean, nullable=False, default=True)

    ballots = db.relationship("Ballot", backref="voting", lazy=True)


class Ballot(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)

    district = db.Column(db.BigInteger, unique=True, nullable=False)
    question = db.Column(db.String, nullable=False)

    candidates = db.relationship("Candidate", backref="ballot", lazy=True)

    voting_id = db.Column(db.BigInteger, db.ForeignKey("voting.id"), nullable=False)


class Candidate(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)

    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    middle_name = db.Column(db.String, nullable=False)

    ballot_id = db.Column(db.BigInteger, db.ForeignKey("ballot.id"), nullable=False)


@app.errorhandler(Exception)
def exc_handler(e=None):
    exc_message = traceback.format_exc()
    app.logger.error(exc_message)
    return f"Internal server error:\n{exc_message}", 500


@app.route("/arm")
def landing():
    votings = Voting.query.all()
    return render_template("landing.html", votings=votings)


@dataclasses.dataclass(frozen=True)
class DistrictCandidateResult:
    candidate_name: str
    candidate_id: int
    candidate_result: int


@dataclasses.dataclass(frozen=True)
class DistrictResult:
    district_id: int
    unique_valid_ballots_amount: int
    invalid_ballots_amount: int

    candidate_results: list[DistrictCandidateResult]


def _human_readable_voting_results(
    blockchain_voting_results: dict[str, Any] | None,
    voting: Voting,
) -> list[DistrictResult] | None:
    if blockchain_voting_results is None:
        return None

    district_candidate_id_to_name = {}
    for ballot in voting.ballots:
        district_id = ballot.district
        current_dict = {}
        for candidate in ballot.candidates:
            current_dict[candidate.id] = (
                f"{candidate.last_name} {candidate.first_name} {candidate.middle_name}"
            )
        district_candidate_id_to_name[district_id] = current_dict

    results = []
    for voting_result in blockchain_voting_results["district_results"].values():
        district_id = voting_result["district_id"]
        unique_valid_ballots_amount = voting_result["unique_valid_ballots_amount"]
        invalid_ballots_amount = voting_result["invalid_ballots_amount"]
        current_candidates = []

        candidate_id_to_candidate_result = {
            int(candidate_id): candidate_result
            for candidate_id, candidate_result in voting_result["tally"].items()
        }
        for candidate_id, candidate_name in district_candidate_id_to_name[
            district_id
        ].items():
            candidate_result = candidate_id_to_candidate_result.get(candidate_id, 0)
            current_candidates.append(
                DistrictCandidateResult(
                    candidate_name=candidate_name,
                    candidate_id=candidate_id,
                    candidate_result=candidate_result,
                )
            )
        results.append(
            DistrictResult(
                district_id=district_id,
                unique_valid_ballots_amount=unique_valid_ballots_amount,
                invalid_ballots_amount=invalid_ballots_amount,
                candidate_results=current_candidates,
            )
        )

    return results


@app.route("/arm/voting/<int:voting_id>")
def get_voting(voting_id):
    voting = Voting.query.get(voting_id)
    try:
        response = requests.get(
            urllib.parse.urljoin(
                app.config["BLOCKCHAIN_SERVICE_URI"],
                "/blockchain_service/voting_state",
            ),
            params={"voting_id": voting.external_voting_id},
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain proxy:\n{err}\n{err.response.text}")

    response_json = response.json()
    voting_state = response_json["state"]
    stored_ballots_amount = response_json.get("stored_ballots_amount")
    decryption_statistics = response_json.get("decryption_statistics")
    voting_results = _human_readable_voting_results(
        response_json.get("voting_results"),
        voting,
    )

    public_key = response_json.get("public_key")
    private_key = response_json.get("private_key")

    return render_template(
        "get_voting.html",
        voting=voting,
        voting_state=voting_state,
        stored_ballots_amount=stored_ballots_amount,
        decryption_statistics=decryption_statistics,
        voting_results=voting_results,
        public_key=public_key,
        private_key=private_key,
        voting_id=voting.external_voting_id,
    )


@app.route("/arm/stop_registration/<int:voting_id>")
def stop_registration(voting_id):
    voting = Voting.query.get(voting_id)
    try:
        response = requests.get(
            urllib.parse.urljoin(
                app.config["BLOCKCHAIN_PROXY_URI"], "/stop_registration"
            ),
            params={"voting_id": voting.external_voting_id},
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain proxy:\n{err}\n{err.response.text}")
    return redirect(url_for("get_voting", voting_id=voting_id))


@app.route("/arm/stop_voting/<int:voting_id>")
def stop_voting(voting_id):
    voting = Voting.query.get(voting_id)
    try:
        response = requests.post(
            urllib.parse.urljoin(
                app.config["BLOCKCHAIN_SERVICE_URI"],
                "/blockchain_service/stop_voting",
            ),
            params={"voting_id": voting.external_voting_id},
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain service:\n{err}\n{err.response.text}")

    voting.is_running = False
    db.session.commit()

    _refresh_deg_caches()

    return redirect(url_for("get_voting", voting_id=voting_id))


@app.route("/arm/start_decryption/<int:voting_id>", methods=["POST"])
def start_decryption(voting_id):
    private_key = request.form["private_key"]
    voting = Voting.query.get(voting_id)
    try:
        response = requests.post(
            urllib.parse.urljoin(
                app.config["BLOCKCHAIN_SERVICE_URI"],
                "/blockchain_service/start_decryption",
            ),
            json={
                "voting_id": voting.external_voting_id,
                "private_key_hex": private_key,
            },
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain service:\n{err}\n{err.response.text}")
    return redirect(url_for("get_voting", voting_id=voting_id))


@app.route("/arm/deanonimize_users/<int:voting_id>", methods=["GET"])
def deanonimize_users(voting_id):
    voting = Voting.query.get(voting_id)
    try:
        response = requests.post(
            urllib.parse.urljoin(
                app.config["BLOCKCHAIN_SERVICE_URI"],
                "/blockchain_service/run_deanonimization",
            ),
            json={
                "voting_id": voting.external_voting_id,
            },
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain service:\n{err}\n{err.response.text}")
    return redirect(url_for("get_voting", voting_id=voting_id))


def _create_voting_relations(public_key, external_voting_id, ballots):
    model_ballots = []
    for ballot in ballots:
        model_candidates = []
        for candidate in ballot["candidates"]:
            model_candidates.append(
                Candidate(
                    id=candidate["id"],
                    first_name=candidate["first_name"],
                    last_name=candidate["last_name"],
                    middle_name=candidate["middle_name"],
                )
            )
        model_ballots.append(
            Ballot(
                district=ballot["district"],
                question=ballot["question"],
                candidates=model_candidates,
            )
        )
    voting = Voting(
        public_key=public_key,
        external_voting_id=external_voting_id,
        ballots=model_ballots,
    )
    db.session.add(voting)
    db.session.commit()
    return voting


@app.route("/arm/refresh_caches", methods=["GET"])
def refresh_caches():
    _refresh_deg_caches()
    return "SUCCESS"


def _concat_candidate_fio(candidate):
    return (
        f"{candidate['last_name']} {candidate['first_name']} {candidate['middle_name']}"
    )


def _create_voting_for_putin(
    public_key: str,
):
    candidate_ids = _generate_candidate_ids(2)
    ballot = {
        "district": 1,
        "question": "Кто лучший президент?",
        "candidates": [
            {
                "id": candidate_ids[0],
                "last_name": "Путин",
                "first_name": "Владимир",
                "middle_name": "Владимирович",
            },
            {
                "id": candidate_ids[1],
                "last_name": "Лутин",
                "first_name": "Василий",
                "middle_name": "Васильевич",
            },
        ],
    }
    blockchain_ballot = {
        "district_id": ballot["district"],
        "question": ballot["question"],
        "min_choices": 1,
        "max_choices": 1,
        "options": {
            candidate["id"]: _concat_candidate_fio(candidate)
            for candidate in ballot["candidates"]
        },
    }

    try:
        create_voting_response = requests.post(
            urllib.parse.urljoin(app.config["BLOCKCHAIN_PROXY_URI"], "/create_voting"),
            json={
                "crypto_system": {"public_key": public_key},
                "revote_enabled": False,
                "ballots_config": [blockchain_ballot],
            },
        )
        create_voting_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain proxy:\n{err}\n{err.response.text}")

    external_voting_id = create_voting_response.json()["voting_id"]

    app.logger.info("Adding Putin voting to the database")
    voting = _create_voting_relations(public_key, external_voting_id, [ballot])

    _refresh_deg_caches()

    return voting.id


@app.route("/arm/create_voting", methods=["GET", "POST"])
def create_voting():
    if request.method == "GET":
        return render_template("create_voting.html")

    app.logger.info(f"Request form: {request.form}")

    public_key = request.form["public_key"]

    voting_id = _create_voting_for_putin(public_key)

    return redirect(url_for("get_voting", voting_id=voting_id))


@app.route("/arm/config", methods=["GET"])
def config():
    site_root = os.path.realpath(os.path.dirname(__file__))
    base_json_path = os.path.join(site_root, "base_config.json")
    with open(base_json_path) as base_json_path_file:
        base_config = json.load(base_json_path_file)

    result = []
    votings = Voting.query.all()
    for voting in votings:
        current_config = copy.deepcopy(base_config)
        current_config["ID"] = voting.id
        current_config["EXT_ID"] = voting.external_voting_id
        current_config["PUBLIC_KEY"] = voting.public_key

        if not voting.is_running:
            current_config["END_TIME"] = "1970-01-1"

        result.append(current_config)

    if not result and not request.args.get("empty_ok"):
        fake_config = copy.deepcopy(base_config)
        fake_config["MDM_SERVICE_URL"] = app.config["FAILING_MDM_URL"]
        result = [fake_config]

    return {"data": result, "error": "0"}


@app.route("/arm/gd", methods=["GET"])
def gd_config():
    ballots = Ballot.query.all()
    result = {}
    for ballot in ballots:
        district = ballot.district
        current_result = {"name": ballot.question}
        for candidate in ballot.candidates:
            current_result[str(candidate.id)] = (
                f"{candidate.id}|{candidate.last_name}|{candidate.first_name}|{candidate.middle_name}|1900-01-01|fake_university|fake_faculty|fake_specialty|fake_logo|fake_photo|fake_description"
            )
        result[district] = current_result
    return {"result": result}


@app.route("/arm/gd_DISTRICT", methods=["GET"])
def gd_district_config():
    ballots = Ballot.query.all()
    result = {}
    for ballot in ballots:
        result[ballot.district] = {"100": "uik_name|1348|uik_address|88005553535"}
    return {"result": result}


with app.app_context():
    while True:
        wait_start = time.time()
        try:
            db.create_all()
            break
        except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.IntegrityError) as e:
            app.logger.error(f"Database creation failed: {e}")
            current_time = time.time()
            if current_time - wait_start > 60:
                raise RuntimeError("Database creation failed in 60 seconds") from e
            time.sleep(4)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
