import pytest

from app.services import road_status


@pytest.fixture(autouse=True)
def _fresh_road_cache():
    road_status.invalidate()
    yield
    road_status.invalidate()
