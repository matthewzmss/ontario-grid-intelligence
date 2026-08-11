"""
IESO Realtime Totals Extractor

Pulls 5-minute real-time grid totals from IESO.
Source: https://reports-public.ieso.ca/public/RealtimeTotals/

Data includes:
- Total Energy (MW)
- Total Loss (MW)
- Total Load (MW)
- Operating Reserves: 10S (spinning), 10N (non-spinning), 30R (30-min)

CSV format is non-standard — has metadata rows and custom headers.
"""

import pandas as pd
from io import StringIO
from etl.base_extractor import BaseExtractor


class RealtimeExtractor(BaseExtractor):
    """Extracts 5-minute real-time grid totals from IESO."""

    EXPECTED_COLUMNS = [
        "hour", "interval", "total_energy", "total_loss",
        "total_load", "total_10s", "total_10n", "total_30r"
    ]

    def __init__(self):
        super().__init__(name="RealtimeExtractor")
        self.endpoint = f"{self.base_url}/RealtimeTotals"

    def _parse_realtime_csv(self, text: str) -> pd.DataFrame:
        """
        Parse IESO's non-standard realtime CSV format.

        The file looks like:
            PM 20260807 \tNORMAL DISPATCH TOTALS;
            RTEM_TOTALS;
            \\CREATED AT 2026/08/07 11:57:28 FOR 2026/08/07
            HOUR,INTERVAL,TOTAL ENERGY,TOTAL LOSS,TOTAL LOAD,...
            13,1,21310.5,475.7,20834.9,...
        """
        lines = text.strip().split("\n")

        # Find the header line (starts with HOUR)
        header_idx = None
        for i, line in enumerate(lines):
            clean = line.strip().strip("\r")
            if clean.upper().startswith("HOUR"):
                header_idx = i
                break

        if header_idx is None:
            self.logger.warning("Could not find header row in realtime CSV")
            return pd.DataFrame()

        # Extract header and data lines
        data_lines = [lines[header_idx]] + lines[header_idx + 1:]
        clean_csv = "\n".join(line.strip().strip("\r") for line in data_lines if line.strip())

        df = pd.read_csv(StringIO(clean_csv))
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Convert numeric columns
        numeric_cols = ["total_energy", "total_loss", "total_load",
                       "total_disp_load_sched_off", "total_10s", "total_10n", "total_30r"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def extract(self) -> pd.DataFrame:
        """Pull the latest real-time totals."""
        url = f"{self.endpoint}/PUB_RealtimeTotals.csv"
        response = self.fetch_url(url)
        df = self._parse_realtime_csv(response.text)

        if not df.empty:
            # Extract date from the file metadata
            for line in response.text.split("\n"):
                if "CREATED AT" in line or "FOR" in line:
                    # Try to extract date from "FOR 2026/08/07"
                    parts = line.split("FOR")
                    if len(parts) > 1:
                        date_str = parts[-1].strip().strip("\r")
                        try:
                            from datetime import datetime
                            df["date"] = datetime.strptime(date_str, "%Y/%m/%d").date()
                        except ValueError:
                            df["date"] = pd.Timestamp.now().date()
                        break

        self.logger.info(f"Realtime totals: {len(df)} rows extracted")
        return df


if __name__ == "__main__":
    extractor = RealtimeExtractor()
    df = extractor.run()
    print(f"\nExtracted {len(df)} rows of realtime data")
    print(df)
