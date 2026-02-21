from typing import List, Dict, Union, Any, Optional
from pydantic import BaseModel, Field

class PlaceholderInfo(BaseModel):
    key: str
    type: str
    idx: int

class LayoutInfo(BaseModel):
    layout_id: int
    layout_name: str
    placeholders: List[PlaceholderInfo]

class TemplateProfile(BaseModel):
    template_name: str
    layouts: List[LayoutInfo]
    allowed_layout_ids: List[int] = Field(default_factory=list)

class SlideField(BaseModel):
    key: str
    value: Union[str, List[str]]

class SlideSpec(BaseModel):
    slide_id: str
    layout_id: int
    fields: List[SlideField]
    notes: Optional[str] = None

class DeckSpec(BaseModel):
    deck_title: str
    slides: List[SlideSpec]

