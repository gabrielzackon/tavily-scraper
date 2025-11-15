import pandas as pd
from .settings import PROJECT_ROOT

RESULTS_DIR = PROJECT_ROOT / "results"

def save_df(df: pd.DataFrame, name: str) -> None:
    """
    Persist a DataFrame as CSV under results/<name>.csv.

    This intentionally keeps the storage layer minimal, but centralizes
    the filesystem layout so it can be replaced later (e.g., S3, DB, etc.).
    """
    if df.empty:
        return
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{name}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
