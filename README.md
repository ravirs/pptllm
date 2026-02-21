# Template-Driven LLM PowerPoint Generator + Editor

A minimal, powerful Streamlit web app that lets you generate and iterate on PowerPoint presentations using your own corporate templates. It ensures brand compliance by using existing slide layouts and placeholders through OpenAI Structured Outputs and `python-pptx`, rather than free-form drawing.

## Features
- **Template Profiling:** Upload a `.pptx` or `.potx` template and the app extracts all available layouts and placeholders automatically.
- **LLM Deck Generation:** Paste a content outline and target slide count, and the app leverages OpenAI to output a strictly validated JSON structure matching your presentation.
- **Corporate Branding:** Render presentations natively using `python-pptx` to perfectly map content to your template's title, body, and footer placeholders.
- **Chat-Style Editing:** Iteratively refine the generated deck by asking for changes ("make slide 3 punchier", "add an agenda slide"), maintaining full version history.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd pptllm
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up your environment variables:**
   Create a `.env` file in the root directory and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-...
   ```

## Usage

Start the Streamlit development server:
```bash
streamlit run app.py
```

1. Navigate to `http://localhost:8501`.
2. Upload your own corporate `.pptx` template or use the provided `sample_template.pptx`.
3. Provide an outline/topic and hit "Generate Deck".
4. Use the Edit module to refine the deck, and download your final `.pptx` file.

## Technical Stack
- **Frontend:** Streamlit
- **Backend/Logic:** Python
- **PPTX Engine:** `python-pptx`
- **LLM/Validation:** `openai` (Structured Outputs), `pydantic`
