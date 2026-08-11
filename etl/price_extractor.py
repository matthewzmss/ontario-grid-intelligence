"""
IESO Price Extractor

Pulls electricity price data from IESO:
- HOEP (Hourly Ontario Energy Price) + Predispatch + Operating Reserves
Source: https://reports-public.ieso.ca/public/PriceHOEPPredispOR/

CSV format:
    Date, Hour, HOEP, Hour 1 Predispatch, ..., OR 10 Min Sync, OR 10 Min non-sync, OR 30 Min
"""

import pandas as pd
from io import StringIO
from etl.base_extractor import BaseExtractor


class PriceExtractor(BaseExtractor):
    """Extracts HOEP price data from IESO."""

    EXPECTED_COLUMNS = ["date", "hour", "hoep"]

    def __init__(self):
        super().__init__(name="PriceExtractor")
        self.endpoint = f"{self.base_url}/PriceHOEPPredispOR"

    def extract(self) -> pd.DataFrame:
        """Pull current year HOEP price data."""
        url = f"{self.endpoint}/PUB_PriceHOEPPredispOR.csv"
        response = self.fetch_url(url)

        # IESO CSV has metadata rows at the top (lines starting with \\)
        lines = response.text.strip().split("\n")
        data_lines = [line for line in lines if not line.startswith("\\")]
        clean_csv = "\n".join(data_lines)

        df = pd.read_csv(StringIO(clean_csv))
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Standardize column names
        col_renames = {}
        for col in df.columns:
            if col == "date":
                continue
            elif col == "hour":
                continue
            elif col == "hoep":
                continue
            elif "predispatch" in col:
                col_renames[col] = col  # keep as-is
            elif "10_min_sync" in col or "10_min_non" in col or "30_min" in col:
                col_renames[col] = col  # keep as-is

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["hour"] = df["hour"].astype(int)
        df["hoep"] = pd.to_numeric(df["hoep"], errors="coerce")

        # Remove duplicates
        df = df.drop_duplicates(subset=["date", "hour"], keep="last")

        self.validate(df, self.EXPECTED_COLUMNS)
        return df

    def extract_year(self, year: int) -> pd.DataFrame:
        """Pull price data for a specific historical year."""
        url = f"{self.endpoint}/PUB_PriceHOEPPredispOR_{year}.csv"
        self.logger.info(f"Extracting prices for year {year}")

        try:
            response = self.fetch_url(url)
        except Exception:
            self.logger.warning(f"No price data available for year {year}")
            return pd.DataFrame()

        lines = response.text.strip().split("\n")
        data_lines = [line for line in lines if not line.startswith("\\")]
        clean_csv = "\n".join(data_lines)

        df = pd.read_csv(StringIO(clean_csv))
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["hour"] = df["hour"].astype(int)
        df["hoep"] = pd.to_numeric(df["hoep"], errors="coerce")
        df = df.drop_duplicates(subset=["date", "hour"], keep="last")

        self.logger.info(f"Year {year}: {len(df)} rows extracted")
        return df

    def extract_historical(self, start_year: int = 2020, end_year: int = 2026) -> pd.DataFrame:
        """Pull price data for multiple years."""
        all_data = []

        for year in range(start_year, end_year + 1):
            df = self.extract_year(year)
            if not df.empty:
                all_data.append(df)

        if not all_data:
            raise ValueError("No historical price data could be extracted")

        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "hour"], keep="last")
        combined = combined.sort_values(["date", "hour"]).reset_index(drop=True)

        self.logger.info(f"Historical extraction complete: {len(combined)} total rows")
        return combined


if __name__ == "__main__":
    extractor = PriceExtractor()
    df = extractor.run()
    print(f"\nExtracted {len(df)} rows of price data")
    print(df.head(10))
    print(f"\nPrice range: ${df['hoep'].min():.2f} to ${df['hoep'].max():.2f}/MWh")
