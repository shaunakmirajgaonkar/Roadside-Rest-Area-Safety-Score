# Roadside Rest-Area Safety Score

A privacy-conscious, local-first Streamlit dashboard for screening highway rest areas using lighting, sanitation, accessibility, crowding, emergency support and verified user-report signals.

## Highlights
- Explainable 0–100 safety score
- Low / Moderate / High / Critical risk screening
- Six-pillar safety profile
- Priority queue and facility explorer
- Safety matrix and zone benchmarking
- Verified user-report evidence view
- Inspection freshness view
- Rule-based review actions
- What-if scenario lab
- Local CSV upload and filtered export
- No external APIs

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Data
Bundled sample CSVs are in `data/`. The app works fully locally.
