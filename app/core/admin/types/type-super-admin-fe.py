from dataclasses import dataclass
from typing import Optional


@dataclass
class SuperadminFrontendPage:
    id: int
    title: Optional[str]
    slug: str
    content: str
    is_shown: bool
    menu_order: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]

# Example instantiation
page = SuperadminFrontendPage(
    id=1,
    title="Example Page",
    slug="example-page",
    content="This is the content of the example page.",
    is_shown=True,
    menu_order=1,
    created_at="2024-05-03 10:00:00",
    updated_at="2024-05-03 10:05:00"
)
