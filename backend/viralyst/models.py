"""The data shapes Viralyst passes around.

A dataclass is a tidy container for related values. Defining them all in
one place makes it clear what every other file expects to receive.
"""

from dataclasses import dataclass


@dataclass
class VideoBrief:
    """What we know about the video.

    In Phase 4 an AI will fill this in by actually watching the video.
    For now we write it by hand in a JSON file.
    """

    title: str
    description: str
    topics: list[str]
    length_seconds: int
    hook_strength: float  # 0-1: do the first 3 seconds stop the scroll?
    quality: float  # 0-1: clear, well paced, good audio and visuals
    shareability: float  # 0-1: would you send this to a friend?
    save_value: float  # 0-1: worth saving to come back to later?


@dataclass
class Audience:
    """Who the video was made for."""

    interests: list[str]
    min_age: int
    max_age: int


@dataclass
class Persona:
    """One simulated Instagram user."""

    name: str
    age: int
    interests: list[str]
    in_target: bool  # part of the audience the video was made for?
    pickiness: float  # 0-1: how hard they are to impress
    share_tendency: float  # 0-1: how often they send reels to friends
    attention_span: int  # seconds before they get restless


@dataclass
class Reaction:
    """What one persona did after the video appeared in their feed."""

    persona: Persona
    watch_fraction: float  # 0-1: how much of the video they watched
    liked: bool = False
    commented: bool = False
    shared: bool = False
    saved: bool = False
    followed: bool = False

    @property
    def scrolled_past(self) -> bool:
        return self.watch_fraction < 0.15


@dataclass
class Wave:
    """One round of distribution: who Instagram shows the video to next."""

    label: str
    size: int  # how many personas we simulate
    target_fraction: float  # share of this crowd that is in the target audience
    represents: int  # rough number of real people this wave stands for


@dataclass
class WaveResult:
    """What happened in one wave, and what the algorithm decided."""

    number: int
    wave: Wave
    reactions: list[Reaction]
    rates: dict[str, float]
    score: float
    threshold: float

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold
