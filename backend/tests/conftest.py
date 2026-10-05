"""Shared test setup. pytest loads this file automatically.

A fixture is a function that prepares something tests need. Any test that
takes a parameter named `good_demo` receives what the fixture returns.
"""

import json
from pathlib import Path

import pytest

from viralyst.models import Audience, VideoBrief

EXAMPLES = Path(__file__).parent.parent / "examples"


def load(name: str) -> tuple[VideoBrief, Audience]:
    data = json.loads((EXAMPLES / name).read_text())
    return VideoBrief(**data["video"]), Audience(**data["audience"])


@pytest.fixture
def good_demo() -> tuple[VideoBrief, Audience]:
    return load("good_demo.json")


@pytest.fixture
def weak_demo() -> tuple[VideoBrief, Audience]:
    return load("weak_demo.json")
