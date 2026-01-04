from pathlib import Path
from Ingestion.core.loader import load_file

pdf = Path("data/samples/CrystalcloudDoc").glob("*.pdf")

for file in pdf:
    text = load_file(file)
    print(file.name, "→", len(text), "chars")
