from pathlib import Path

import pytest

from app.domain import CatalogSnapshot

SEED_DIR = Path(__file__).resolve().parents[1] / "seeds" / "catalog"


@pytest.fixture(scope="session")
def seed_dir() -> Path:
    return SEED_DIR


@pytest.fixture(scope="session")
def snapshot(seed_dir: Path) -> CatalogSnapshot:
    """The real seed catalog — tests double as the CI seed-validation gate."""
    from app.knowledge.seed_catalog import load_seed_snapshot

    return load_seed_snapshot(seed_dir)
