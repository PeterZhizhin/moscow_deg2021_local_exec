import os

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(os.getcwd(), 'database', 'db.sqlite')

BLOCKCHAIN_PROXY_URI = os.environ.get("BLOCKCHAIN_PROXY_URI", "http://localhost:8021")

REFRESH_CACHE_URLS = os.environ.get("REFRESH_CACHE_URLS", "http://deg_ballot:8003/webhook/refresh-cache;http://deg_form:8004/webhook/refresh-cache;http://deg_componentx:8002/webhook/refresh-cache;http://blockchain_votes_processor/blockchain_connector/refresh")
REFRESH_CACHE_SYSTEM = os.environ.get("REFRESH_CACHE_SYSTEM", "TestSystem")
REFRESH_CACHE_TOKEN = os.environ.get("REFRESH_CACHE_TOKEN", "TOKEN_SECRET")

# This is the url that will always fail checkBallot check
# This is a crutch because we cannot return no votings due to a bug in deg_ballot
FAILING_MDM_URL = os.environ.get("FAILING_MDM_URL", "http://fake_mdm/failing")
