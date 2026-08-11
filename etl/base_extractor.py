"""
Base extractor class for IESO data sources.

All extractors inherit from this class and get:
- Automatic retry with exponential backoff
- Structured logging
- Data validation before loading
- Consistent error handling
"""

import time
import logging
import requests
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BaseExtractor:
    """Base class for all IESO data extractors."""

    def __init__(self, name: str, base_url: str = "https://reports-public.ieso.ca/public"):
        self.name = name
        self.base_url = base_url
        self.logger = logging.getLogger(self.name)

    def fetch_url(self, url: str, max_retries: int = 3) -> requests.Response:
        """
        Fetch a URL with automatic retry and exponential backoff.

        If the request fails, it waits 2s, then 4s, then 8s before retrying.
        This handles temporary IESO server issues gracefully.
        """
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Fetching: {url} (attempt {attempt}/{max_retries})")
                response = requests.get(url, timeout=30)
                response.raise_for_status()  # Raises error for 4xx/5xx status codes
                self.logger.info(f"Success: {len(response.content)} bytes received")
                return response

            except requests.exceptions.RequestException as e:
                wait_time = 2 ** attempt  # 2s, 4s, 8s
                self.logger.warning(f"Attempt {attempt} failed: {e}")

                if attempt < max_retries:
                    self.logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} attempts failed for {url}")
                    raise

    def fetch_csv(self, url: str, **kwargs) -> pd.DataFrame:
        """Fetch a CSV file from a URL and return as a DataFrame."""
        response = self.fetch_url(url)
        from io import StringIO
        return pd.read_csv(StringIO(response.text), **kwargs)

    def validate(self, df: pd.DataFrame, expected_columns: list[str]) -> bool:
        """
        Validate that a DataFrame has the expected columns and isn't empty.
        Returns True if valid, raises ValueError if not.
        """
        if df.empty:
            raise ValueError(f"{self.name}: DataFrame is empty — no data extracted")

        missing = set(expected_columns) - set(df.columns)
        if missing:
            raise ValueError(f"{self.name}: Missing columns: {missing}")

        row_count = len(df)
        self.logger.info(f"Validation passed: {row_count} rows, {len(df.columns)} columns")
        return True

    def add_metadata(self, df: pd.DataFrame, source_url: str) -> pd.DataFrame:
        """Add metadata columns to track when and where data was loaded from."""
        df = df.copy()
        df["_loaded_at"] = datetime.utcnow()
        df["_source"] = source_url
        return df

    def extract(self) -> pd.DataFrame:
        """Override this method in each extractor to pull specific data."""
        raise NotImplementedError("Each extractor must implement extract()")

    def run(self) -> pd.DataFrame:
        """Execute the full extract → validate → add metadata pipeline."""
        self.logger.info(f"Starting extraction: {self.name}")
        start_time = time.time()

        df = self.extract()
        df = self.add_metadata(df, source_url=self.base_url)

        elapsed = round(time.time() - start_time, 2)
        self.logger.info(f"Extraction complete: {len(df)} rows in {elapsed}s")
        return df
