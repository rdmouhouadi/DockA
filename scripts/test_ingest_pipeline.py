from pathlib import Path
from Ingestion.pipelines.ingest_folder import ingest_folder

folder = Path("data/samples/CrystalcloudDoc")

result = ingest_folder(folder)

print("Ingestion summary:", result)
