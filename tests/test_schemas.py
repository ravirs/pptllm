from core.schemas import DeckSpec, SlideSpec, TemplateProfile, LayoutInfo, PlaceholderInfo

def test_deck_spec_validation():
    data = {
        "deck_title": "Test Presentation",
        "slides": [
            {
                "slide_id": "1",
                "layout_id": 0,
                "fields": [
                    {"key": "title", "value": "Main Title"},
                    {"key": "subtitle", "value": "A subtitle"}
                ]
            },
             {
                "slide_id": "2",
                "layout_id": 1,
                "fields": [
                    {"key": "title", "value": "Bullet Slide"},
                    {"key": "body", "value": ["Point 1", "Point 2"]}
                ]
            }
        ]
    }
    spec = DeckSpec(**data)
    assert spec.deck_title == "Test Presentation"
    assert len(spec.slides) == 2
    assert spec.slides[1].fields[1].value == ["Point 1", "Point 2"]
    
def test_template_profile_validation():
    data = {
        "template_name": "Test.pptx",
        "layouts": [
            {
                "layout_id": 0,
                "layout_name": "Title",
                "placeholders": [
                    {"key": "title", "type": "TITLE", "idx": 0}
                ]
            }
        ]
    }
    profile = TemplateProfile(**data)
    assert profile.template_name == "Test.pptx"
    assert len(profile.layouts) == 1
    assert profile.allowed_layout_ids == [] # check default factory
