python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python src/eda_v1.0.py --input data/Superstore.csv --outdir reports --title "Retail EDA  MVP 1.0"
