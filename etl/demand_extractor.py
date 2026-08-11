"""
IESO Demand Extractor

Pulls hourly demand data (Market Demand + Ontario Demand) from IESO public reports.
Source: https://reports-public.ieso.ca/public/Demand/

Data format (CSV):
    Date, Hour, Market Demand, Ontario Demand
    2026-01-01, 1, 19489, 16526
    2026-01-01, 2, 19317, 16374
    ...

- One row per hour (24 rows per day)
- Historical files available by year: PUB_Demand_YYYY.csv
- Current year file: PUB_Demand.csv (updated hourly)
"""

import pandas as pd
from io import StringIO
from etl.base_extractor import BaseExtractor


class DemandExtractor(BaseExtractor):
    """Extracts hourly demand data from IESO."""

    EXPECTED_COLUMNS = ["date", "hour", "market_demand", "ontario_demand"]

    def __init__(self):
        super().__init__(name="DemandExtractor")
        self.endpoint = f"{self.base_url}/Demand"

    def extract(self) -> pd.DataFrame:
        """Pull current year demand data from IESO."""
        url = f"{self.endpoint}/PUB_Demand.csv"
        response = self.fetch_url(url)

        # IESO CSV has metadata rows at the top (lines starting with \\)
        # We need to skip those and find the actual header row
        lines = response.text.strip().split("\n")
        data_lines = [line for line in lines if not line.startswith("\\")]
        clean_csv = "\n".join(data_lines)

        df = pd.read_csv(StringIO(clean_csv))

        # Standardize column names
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Ensure correct types
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["hour"] = df["hour"].astype(int)
        df["market_demand"] = pd.to_numeric(df["market_demand"], errors="coerce")
        df["ontario_demand"] = pd.to_numeric(df["ontario_demand"], errors="coerce")

        # Remove duplicates (IESO sometimes publishes overlapping data)
        df = df.drop_duplicates(subset=["date", "hour"], keep="last")

        self.validate(df, self.EXPECTED_COLUMNS)
        return df

    def extract_year(self, year: int) -> pd.DataFrame:
        """Pull demand data for a specific historical year."""
        url = f"{self.endpoint}/PUB_Demand_{year}.csv"
        self.logger.info(f"Extracting demand for year {year}")

        try:
            response = self.fetch_url(url)
        except Exception:
            self.logger.warning(f"No demand data available for year {year}")
            return pd.DataFrame()

        lines = response.text.strip().split("\n")
        data_lines = [line for line in lines if not line.startswith("\\")]
        clean_csv = "\n".join(data_lines)

        df = pd.read_csv(StringIO(clean_csv))
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["hour"] = df["hour"].astype(int)
        df["market_demand"] = pd.to_numeric(df["market_demand"], errors="coerce")
        df["ontario_demand"] = pd.to_numeric(df["ontario_demand"], errors="coerce")
        df = df.drop_duplicates(subset=["date", "hour"], keep="last")

        self.logger.info(f"Year {year}: {len(df)} rows extracted")
        return df

    def extract_historical(self, start_year: int = 2020, end_year: int = 2026) -> pd.DataFrame:
        """Pull demand data for multiple years and combine into one DataFrame."""
        all_data = []

        for year in range(start_year, end_year + 1):
            df = self.extract_year(year)
            if not df.empty:
                all_data.append(df)

        if not all_data:
            raise ValueError("No historical demand data could be extracted")

        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "hour"], keep="last")
        combined = combined.sort_values(["date", "hour"]).reset_index(drop=True)

        self.logger.info(f"Historical extraction complete: {len(combined)} total rows")
        return combined


# Allow running this extractor directly: python -m etl.demand_extractor
if __name__ == "__main__":
    extractor = DemandExtractor()
    df = extractor.run()
    print(f"\nExtracted {len(df)} rows of demand data")
    print(df.head(10))
    print(f"\nDate range: {df['date'].min()} to {df['date'].max()}")
