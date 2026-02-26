import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from core.schemas import TemplateProfile, DeckSpec

# --- State ---
class AgentState(TypedDict):
    profile: TemplateProfile
    prompt: str
    slide_count: str
    tone: str
    template_path: str
    
    # Internal variables passed between agents
    layouts_context: str
    planned_outline: str
    draft_deck_spec: Optional[DeckSpec]
    
    # Validation loop
    review_feedback: str
    review_passed: bool
    iterations: int

# Initialize LLM
# Note: We configure it identically to the single-agent but pass it natively
api_key = os.environ.get("OPENAI_API_KEY", "").strip(' \t\n\r"“”\'')
llm = ChatOpenAI(model="gpt-4o-2024-08-06", api_key=api_key) if api_key else ChatOpenAI(model="gpt-4o-2024-08-06")

# --- Nodes (Agents) ---

def context_builder(state: AgentState) -> AgentState:
    """Extracts formatting string summarizing allowed layouts."""
    profile = state["profile"]
    layouts_summary = []
    for layout in profile.layouts:
        if layout.layout_id in profile.allowed_layout_ids:
            allowed_keys = [p.key for p in layout.placeholders]
            layouts_summary.append(f"- Layout ID: {layout.layout_id}, Name: '{layout.layout_name}', Allowed Fields: {allowed_keys}")
    
    return {"layouts_context": "\n".join(layouts_summary)}

def planner_agent(state: AgentState) -> AgentState:
    """Agent 1: Designs a detailed slide-by-slide narrative outline without worrying about JSON mapping yet."""
    sys_msg = SystemMessage(content="You are a Master Presentation Strategist. Design a compelling narrative outline for a presentation.")
    user_msg = HumanMessage(content=(
        f"Topic/Instructions: {state['prompt']}\n"
        f"Target Slide Count: {state['slide_count']}\n"
        f"Audience/Tone: {state['tone']}\n\n"
        f"Provide a comprehensive outline. For each slide, define the Title, the core message, and specific bullet points or talking data."
    ))
    
    # Standard text completion
    response = llm.invoke([sys_msg, user_msg])
    return {"planned_outline": response.content}

def writer_agent(state: AgentState) -> AgentState:
    """Agent 2: Maps the narrative outline to the exact JSON schema and allowed PPT Layouts."""
    
    # Let's bind the LLM to strictly output our DeckSpec Pydantic schema
    structured_llm = llm.with_structured_output(DeckSpec)
    
    sys_msg = SystemMessage(content="You are an expert PowerPoint Deck Builder. You must map the provided presentation outline into the exact structured JSON format required by the corporate template.")
    
    content = (
        f"Template Layouts Context:\n{state['layouts_context']}\n\n"
        f"Presentation Outline (from Strategist):\n{state['planned_outline']}\n\n"
    )
    
    if state.get("iterations", 0) > 0 and not state.get("review_passed", True):
        content += f"CRITICAL: The previous generation failed validation with this error:\n{state['review_feedback']}\n\nPlease fix these errors and regenerate."
        
    user_msg = HumanMessage(content=content)
    
    try:
        deck_spec = structured_llm.invoke([sys_msg, user_msg])
        return {"draft_deck_spec": deck_spec}
    except Exception as e:
        return {"draft_deck_spec": None, "review_feedback": str(e), "review_passed": False}

def reviewer_agent(state: AgentState) -> AgentState:
    """Agent 3: Validates the drafted JSON to ensure it meets constraints logically."""
    # (Structural validation is already handled by Pydantic + structured outputs).
    # We use this as a semantic checking layer (e.g. did it follow slide count roughly?)
    deck = state.get("draft_deck_spec")
    iterations = state.get("iterations", 0) + 1
    
    if not deck:
        return {"review_passed": False, "iterations": iterations}
        
    # Basic semantic check
    if len(deck.slides) == 0:
        return {"review_passed": False, "review_feedback": "The deck has 0 slides generated.", "iterations": iterations}
        
    return {"review_passed": True, "review_feedback": "Passed semantic review. Proceeding to visual validation.", "iterations": iterations}

import tempfile
import base64
from core.renderer import render_pptx, export_to_thumbnails

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def visual_validator(state: AgentState) -> AgentState:
    """Agent 4: Visually validates the drafted JSON by rendering thumbnails and checking for text overflow."""
    deck = state.get("draft_deck_spec")
    template_path = state.get("template_path")
    
    if not template_path:
        return {"review_passed": True, "review_feedback": "Skipped Visual Validation (No template path)."}
        
    iterations = state.get("iterations", 0) + 1
        
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pptx = os.path.join(temp_dir, "temp.pptx")
        temp_img_dir = os.path.join(temp_dir, "images")
        
        # 1. Render temporary presentation
        try:
            render_pptx(template_path, deck, temp_pptx, state["profile"])
        except Exception as e:
            return {"review_passed": False, "review_feedback": f"Visual render failed: {str(e)}", "iterations": iterations}
            
        # 2. Export to images
        images = export_to_thumbnails(temp_pptx, temp_img_dir)
        if not images:
            return {"review_passed": True, "review_feedback": "Skipped Visual Validation (Failed to gen images).", "iterations": iterations}
            
        # 3. Pass to Vision Model
        content = [
            {"type": "text", "text": "You are a Presentation Design QA. Review these slides. Check for ANY text that overflows its bounding box, gets cut off, overlaps awkwardly, or falls off the bottom of the page. If there are NO issues, reply EXACTLY with 'PASS'. If there ARE issues, explain them so the text generation agent can shorten the text."}
        ]
        
        for img_path in images:
            base64_image = encode_image(img_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
            
        sys_msg = SystemMessage(content="You are a strict QA bot.")
        user_msg = HumanMessage(content=content)
        
        try:
            response = llm.invoke([sys_msg, user_msg])
            feedback = response.content.strip()
            
            if "PASS" in feedback.upper() and len(feedback) < 10:
                return {"review_passed": True, "review_feedback": "Visual passed.", "iterations": iterations}
            else:
                return {"review_passed": False, "review_feedback": f"VISUAL QA FAILED. Shorten the text to fix these issues:\n{feedback}", "iterations": iterations}
                
        except Exception as e:
            return {"review_passed": True, "review_feedback": f"Vision API error, skipping. ({str(e)})", "iterations": iterations}

# --- Routing ---
def should_continue_reviewer(state: AgentState) -> str:
    # After semantic reviewer, if failed, go back to writer. If passed, go to visual_validator.
    if not state["review_passed"]:
        if state["iterations"] >= 3:
            return END
        return "writer_node"
    return "visual_validator_node"
    
def should_continue_visual(state: AgentState) -> str:
    if state["review_passed"] or state["iterations"] >= 3:
        return END
    return "writer_node"

# --- Graph Compilation ---
workflow = StateGraph(AgentState)

workflow.add_node("context_node", context_builder)
workflow.add_node("planner_node", planner_agent)
workflow.add_node("writer_node", writer_agent)
workflow.add_node("reviewer_node", reviewer_agent)
workflow.add_node("visual_validator_node", visual_validator)

workflow.set_entry_point("context_node")
workflow.add_edge("context_node", "planner_node")
workflow.add_edge("planner_node", "writer_node")
workflow.add_edge("writer_node", "reviewer_node")

workflow.add_conditional_edges(
    "reviewer_node",
    should_continue_reviewer,
    {
        "writer_node": "writer_node",
        "visual_validator_node": "visual_validator_node",
        END: END
    }
)

workflow.add_conditional_edges(
    "visual_validator_node",
    should_continue_visual,
    {
        "writer_node": "writer_node",
        END: END
    }
)

app = workflow.compile()
