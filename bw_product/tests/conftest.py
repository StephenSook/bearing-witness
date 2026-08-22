import os

import pytest

MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017/bearing_witness")
TEST_DB = "bearing_witness_test"


def _mongod_available() -> bool:
    try:
        from pymongo import MongoClient
        MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500).admin.command("ping")
        return True
    except Exception:
        return False


MONGOD_UP = _mongod_available()

# Under CI the Mongo service container is mandatory: the decision/persistence
# gates skipping would be a FALSE GREEN (a skip reads as pass at the job level).
# Locally the skip stays legitimate (a dev box without mongod).
if os.environ.get("CI") and not MONGOD_UP:
    raise RuntimeError(
        "CI requires mongod (service container down or URI wrong); "
        "skipping the Mongo-gated tests here would be a false green")

needs_mongod = pytest.mark.skipif(
    not MONGOD_UP, reason="no local mongod (run these on the box before any Mongo claim ships)"
)


@pytest.fixture()
def db():
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
    client.drop_database(TEST_DB)
    yield client[TEST_DB]
    client.drop_database(TEST_DB)
    client.close()
