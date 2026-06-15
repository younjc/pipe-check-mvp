# 🚰 PipeCheck MVP

A Streamlit web app that helps NYC residents identify whether their home's water service line contains lead — using both official city records and AI-powered photo analysis.

## What It Does

PipeCheck offers two tools:

**NYC Address Lookup** — Queries the NYC Department of Environmental Protection (DEP) open database to retrieve the reported material of your building's water service line. Results are categorized as Lead, Possible Lead (galvanized), Non-Lead, or Unknown.

**Photo Analysis AI** — Upload a photo of your pipe and get a material estimate from GPT-4o. The model takes into account physical test results you provide (scratch color, magnet test) and returns a probability estimate with reasoning and next steps.

## Getting Started

### Prerequisites

- Python 3.8+
- An OpenAI API key (required for the Photo Analysis tool only)

### Installation

```bash
git clone https://github.com/younjc/pipe-check-mvp.git
cd pipe-check-mvp
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`.

## Usage

### NYC Address Lookup

1. Select **🔎 NYC Address Lookup** from the sidebar.
2. Enter a NYC street address (e.g., `30-29 33 STREET`).
3. Click **Search Database**.

The app queries the NYC DEP ArcGIS service and returns the reported pipe material along with a risk classification.

### Photo Analysis AI

1. Select **📸 Photo Analysis AI** from the sidebar.
2. Enter your OpenAI API key in the sidebar.
3. Follow the on-screen scratch and magnet test instructions.
4. Upload a photo of your pipe and click **Analyze Photo**.

The app sends the image and your test results to GPT-4o and returns a material estimate with confidence level and recommended next steps.

> **Note:** AI analysis is an estimate only and is not a substitute for laboratory testing.

## Tech Stack

- [Streamlit](https://streamlit.io/) — UI framework
- [OpenAI Python SDK](https://github.com/openai/openai-python) — GPT-4o vision calls
- [NYC DEP Open Data](https://www.nyc.gov/site/dep/index.page) via ArcGIS REST API — service line records

## Disclaimer

This tool is for informational purposes only. AI-generated material estimates are probabilistic and may be inaccurate. Always consult a licensed plumber or certified lab for definitive results. NYC DEP data may be incomplete or out of date.
