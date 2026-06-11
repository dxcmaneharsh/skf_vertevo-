# SKF Project (skfv2)

This repository contains the SKF data processing app and sample data.

## Contents
- `skf_app.py` - main application
- `create_dict.py`, `generate_skf_data.py` - data utilities
- `skf_sample_data_1yr.csv`, `skf_sample_data_v2.csv`, `skf_sample_data_v3_variations.csv` - sample datasets

## Setup
1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run
Run the main app:

```bash
python skf_app.py
```

## Notes
- `Procfile` and `runtime.txt` are included for Heroku deployment.
- Sample data files are provided in the repository root.

## License
Add a license if you want to publish this project publicly.
