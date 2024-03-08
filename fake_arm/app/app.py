import dataclasses
from typing import Any

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, url_for

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


class Voting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    external_voting_id = db.Column(db.String, nullable=False)
    public_key = db.Column(db.String, nullable=False)
    is_running = db.Column(db.Boolean, nullable=False, default=True)

    ballots = db.relationship("Ballot", backref="voting", lazy=True)


class Ballot(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    district = db.Column(db.Integer, unique=True, nullable=False)
    question = db.Column(db.String, nullable=False)

    candidates = db.relationship("Candidate", backref="ballot", lazy=True)

    voting_id = db.Column(db.Integer, db.ForeignKey("voting.id"), nullable=False)


class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    middle_name = db.Column(db.String, nullable=False)

    ballot_id = db.Column(db.Integer, db.ForeignKey("ballot.id"), nullable=False)


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


def _parse_candidates(candidates):
    candidates = [x.strip() for x in candidates.strip().split("\n") if x.strip()]
    if not candidates:
        raise ValueError("Empty candidates list")
    candidates_parsed = []
    existing_ids = set()

    candidate_ids = [
        _generate_candidate_id(existing_ids) for _ in range(len(candidates))
    ]
    candidate_ids.sort()

    for candidate_id, candidate in zip(candidate_ids, candidates):
        last_name, first_name, middle_name = candidate.split()
        candidates_parsed.append(
            {
                "id": candidate_id,
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
            }
        )
        existing_ids.add(candidates_parsed[-1]["id"])
    if len(candidates) <= 1:
        raise ValueError("Not enough candidates")
    blockchain_options = {
        x["id"]: "{} {} {}".format(x["last_name"], x["first_name"], x["middle_name"])
        for x in candidates_parsed
    }
    return candidates_parsed, blockchain_options


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


@app.route("/arm/create_voting", methods=["GET", "POST"])
def create_voting():
    if request.method == "GET":
        return render_template("create_voting.html")
    print(f"Request form: {request.form}")

    public_key = request.form["public_key"]

    ballots = collections.defaultdict(dict)
    for key, value in request.form.items():
        if key == "public_key":
            continue
        key, ballot_id = key.split("_")
        ballot_id = int(ballot_id)
        ballots[ballot_id][key] = value

    result_ballots = []
    result_blockchain_ballots = []
    for ballot in ballots.values():
        district = int(ballot["district"])
        question = ballot["question"]
        candidates, blockchain_options = _parse_candidates(ballot["candidates"])
        result_ballots.append(
            {
                "district": district,
                "question": question,
                "candidates": candidates,
            }
        )
        result_blockchain_ballots.append(
            {
                "district_id": district,
                "question": question,
                "options": blockchain_options,
                "min_choices": 1,
                "max_choices": 1,
            }
        )

    try:
        create_voting_response = requests.post(
            urllib.parse.urljoin(app.config["BLOCKCHAIN_PROXY_URI"], "/create_voting"),
            json={
                "crypto_system": {"public_key": public_key},
                "revote_enabled": True,
                "ballots_config": result_blockchain_ballots,
            },
        )
        create_voting_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise ValueError(f"Error from blockchain proxy:\n{err}\n{err.response.text}")

    external_voting_id = create_voting_response.json()["voting_id"]

    app.logger.info("Adding voting to the database")
    voting = _create_voting_relations(public_key, external_voting_id, result_ballots)

    _refresh_deg_caches()

    return redirect(url_for("get_voting", voting_id=voting.id))


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
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
