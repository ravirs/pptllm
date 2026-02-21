import streamlit as st
import os
import io
import json
from dotenv import load_dotenv

load_dotenv()

from core.template_profiler import profile_template
from core.llm_client import generate_deck, edit_deck
from core.renderer import render_pptx
from core.utils import save_uploaded_file

st.set_page_config(page_title="PPT Generator", layout="wide")

# Initialize Session State
if "template_profile" not in st.session_state:
    st.session_state.template_profile = None
if "template_path" not in st.session_state:
    st.session_state.template_path = None
if "deck_history" not in st.session_state:
    st.session_state.deck_history = []  # List of DeckSpec objects
if "current_deck_idx" not in st.session_state:
    st.session_state.current_deck_idx = -1
if "ppt_bytes" not in st.session_state:
    st.session_state.ppt_bytes = None

def render_preview_to_bytes(deck_spec, template_path, template_profile):
    """Renders the PPTX to a bytes buffer."""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        render_pptx(template_path, deck_spec, tmp.name, template_profile)
        with open(tmp.name, "rb") as f:
            ppt_bytes = f.read()
    try:
        os.remove(tmp.name)
    except:
        pass
    return ppt_bytes

# --- Sidebar ---
st.sidebar.title("Settings")
slide_count = st.sidebar.number_input("Target Slide Count", min_value=1, max_value=50, value=10)
tone = st.sidebar.selectbox("Audience / Tone", ["Formal / Executive", "Neutral / Informative", "Casual", "Technical"])

if st.sidebar.button("Clear Session"):
    for key in ["template_profile", "template_path", "deck_history", "current_deck_idx", "ppt_bytes"]:
        st.session_state[key] = None if key != "deck_history" else []
        if key == "current_deck_idx": st.session_state[key] = -1
    st.sidebar.success("Session cleared.")
    st.rerun()

# --- Main Flow ---
st.title("PPT Generator + Editor")

# Step 1: Upload Template
st.header("Step 1: Upload Template")
uploaded_file = st.file_uploader("Upload a .pptx or .potx file", type=["pptx", "potx"], key="uploader")

if uploaded_file is not None and st.session_state.template_profile is None:
    with st.spinner("Profiling template..."):
        file_path = save_uploaded_file(uploaded_file)
        if file_path:
            st.session_state.template_path = file_path
            st.session_state.template_profile = profile_template(file_path, uploaded_file.name)
        else:
            st.error("Failed to save the uploaded file.")

if st.session_state.template_profile:
    st.success(f"Loaded template: {st.session_state.template_profile.template_name}")
    with st.expander("Detected Layouts & Placeholders"):
        # Let users uncheck some allowed layouts
        selected_ids = []
        for layout in st.session_state.template_profile.layouts:
            keys = [p.key for p in layout.placeholders]
            if st.checkbox(f"[{layout.layout_id}] {layout.layout_name} (Fields: {', '.join(keys)})", value=True, key=f"chk_layout_{layout.layout_id}"):
                selected_ids.append(layout.layout_id)
        
        # Update allowed IDs in state
        st.session_state.template_profile.allowed_layout_ids = selected_ids

    # Step 2: Generate Initial Deck
    st.header("Step 2: Generate Deck")
    
    prompt = st.text_area("Content Prompt / Outline", height=150, placeholder="Paste your outline or presentation topic here...")
    
    if st.button("Generate Deck"):
        if not prompt.strip():
            st.warning("Please provide a prompt.")
        elif not os.environ.get("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY environment variable is not set.")
        else:
            with st.spinner("Generating deck... This may take up to 20-30 seconds."):
                try:
                    deck_spec = generate_deck(
                        profile=st.session_state.template_profile,
                        prompt=prompt,
                        slide_count=str(slide_count),
                        tone=tone
                    )
                    st.session_state.deck_history = [deck_spec]
                    st.session_state.current_deck_idx = 0
                    st.session_state.ppt_bytes = render_preview_to_bytes(deck_spec, st.session_state.template_path, st.session_state.template_profile)
                    st.success("Generation complete!")
                except Exception as e:
                    st.error(f"Generation failed: {e}")

# Step 3: Editor
if len(st.session_state.deck_history) > 0:
    st.divider()
    st.header("Step 3: Edit and Download")
    
    current_deck = st.session_state.deck_history[st.session_state.current_deck_idx]
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Text Preview")
        # Lightweight Text Preview
        st.markdown(f"**Deck Title:** {current_deck.deck_title}")
        for slide in current_deck.slides:
            st.markdown(f"---")
            st.markdown(f"**Slide {slide.slide_id} (Layout {slide.layout_id})**")
            for field in slide.fields:
                k = field.key
                v = field.value
                if isinstance(v, list):
                    st.markdown(f"**{k}:**")
                    for bullet in v:
                        st.markdown(f"- {bullet}")
                else:
                    st.markdown(f"**{k}:** {v}")
                    
    with col2:
        st.markdown("### Actions")
        if st.session_state.ppt_bytes:
            st.download_button(
                label="Download PPTX",
                data=st.session_state.ppt_bytes,
                file_name="generated_deck.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary"
            )
        
        st.markdown("#### Edit Instructions")
        edit_instruction = st.text_input("E.g., 'Make the title of slide 2 more punchy'")
        if st.button("Apply Edits"):
            if edit_instruction.strip() and os.environ.get("OPENAI_API_KEY"):
                with st.spinner("Applying edits..."):
                    try:
                        new_deck = edit_deck(st.session_state.template_profile, current_deck, edit_instruction)
                        # Keep max 5 history states
                        st.session_state.deck_history = st.session_state.deck_history[:st.session_state.current_deck_idx + 1]
                        st.session_state.deck_history.append(new_deck)
                        if len(st.session_state.deck_history) > 5:
                            st.session_state.deck_history.pop(0)
                        
                        st.session_state.current_deck_idx = len(st.session_state.deck_history) - 1
                        st.session_state.ppt_bytes = render_preview_to_bytes(new_deck, st.session_state.template_path, st.session_state.template_profile)
                        st.success("Edits applied!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Edit failed: {e}")
            else:
                st.warning("Please provide edit instructions and ensure API Key is set.")
                
        # Version control
        if len(st.session_state.deck_history) > 1:
            st.markdown("#### History")
            cols = st.columns(len(st.session_state.deck_history))
            for i in range(len(st.session_state.deck_history)):
                with cols[i]:
                    if st.button(f"v{i+1}", disabled=(i == st.session_state.current_deck_idx), key=f"btn_v{i}"):
                        st.session_state.current_deck_idx = i
                        deck = st.session_state.deck_history[i]
                        st.session_state.ppt_bytes = render_preview_to_bytes(deck, st.session_state.template_path, st.session_state.template_profile)
                        st.rerun()

