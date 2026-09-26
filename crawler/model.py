"""The shape every source returns: one collected item (before filtering and attaching)."""
from dataclasses import asdict, dataclass, field


@dataclass
class Item:
    source: str                 # module NAME, e.g. "qnet"
    source_id: str              # id inside that source, stable across runs
    type: str                   # support | scholarship | course | contest | experience | resource
    title: str
    provider: str
    url: str                    # official page for people (not the API endpoint)
    summary: str = ""           # our own short text, never copied source prose beyond facts
    apply_start: str | None = None   # YYYY-MM-DD
    apply_end: str | None = None     # YYYY-MM-DD
    deadline_text: str = ""     # free text when no date ("예산 소진 시", "상시")
    event_start: str | None = None
    event_end: str | None = None
    regions: list[str] = field(default_factory=list)   # help schema codes; [] = unknown
    age_min: int | None = None
    age_max: int | None = None
    target_text: str = ""       # raw eligibility text for the youth filter
    cost_text: str = ""
    tags: list[str] = field(default_factory=list)      # hints for attach rules (e.g. qualification code)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, "", [], {})}
