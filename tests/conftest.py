import pytest
from testcontainers.community.postgres import PostgresContainer

from app import db
from app.embedding import FastembedEmbedder

PG_IMAGE = "pgvector/pgvector:0.8.6-pg18"


@pytest.fixture(scope="session")
def datenbank_url():
    with PostgresContainer(PG_IMAGE, driver=None) as pg:
        url = pg.get_connection_url()
        db.migriere(url, dimension=384)
        yield url


@pytest.fixture
def conn(datenbank_url):
    with db.verbinde(datenbank_url) as conn:
        conn.execute("TRUNCATE dokumente CASCADE")
        conn.commit()
        yield conn


@pytest.fixture(scope="session")
def embedder():
    return FastembedEmbedder()
