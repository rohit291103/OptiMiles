"""Catalog snapshot versioning (D-2 lineage).

The version is a content hash over the catalog's domain objects — not file
bytes, not DB timestamps — so the same catalog content yields the same
version whether it was loaded from seed YAML or from the database. Same goal
+ same context + same snapshot version ⇒ byte-identical results.
"""

import datetime
import hashlib
import json
import uuid
from collections.abc import Iterable
from decimal import Decimal

from pydantic import BaseModel


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        # Numerically-equal Decimals must hash identically: 3.33 == 3.330.
        # format(..., "f") avoids normalize()'s scientific notation (1E+2).
        return format(value.normalize(), "f")
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime.date | datetime.datetime):
        return value.isoformat()
    raise TypeError(f"unhashable catalog field type: {type(value)!r}")


def content_version(object_groups: Iterable[Iterable[BaseModel]]) -> str:
    digest = hashlib.sha256()
    for group in object_groups:
        for obj in sorted(group, key=lambda o: str(getattr(o, "id"))):  # noqa: B009
            digest.update(
                json.dumps(
                    obj.model_dump(mode="python"), sort_keys=True, default=_json_default
                ).encode()
            )
    return f"cat-{digest.hexdigest()[:12]}"
