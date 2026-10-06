"""Read and write the JSON files that describe videos and audiences."""

import json
from dataclasses import asdict
from pathlib import Path

from .models import Archetype, Audience, VideoBrief


def audience_from_dict(data: dict) -> Audience:
    archetypes = [Archetype(**a) for a in data.get("archetypes", [])]
    return Audience(**{**data, "archetypes": archetypes})


def load_audience(path: str | Path) -> Audience:
    return audience_from_dict(json.loads(Path(path).read_text()))


def save_audience(audience: Audience, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(asdict(audience), indent=2, ensure_ascii=False) + "\n")


def load_archetypes(path: str | Path) -> list[Archetype]:
    return [Archetype(**a) for a in json.loads(Path(path).read_text())]


def load_example(path: str | Path) -> tuple[VideoBrief, Audience]:
    """An example file holds a video and its audience. The audience is either written out
    in place, or is the name of a separate audience file in the same folder."""
    data = json.loads(Path(path).read_text())
    audience = data["audience"]
    if isinstance(audience, str):
        return VideoBrief(**data["video"]), load_audience(Path(path).parent / audience)
    return VideoBrief(**data["video"]), audience_from_dict(audience)
