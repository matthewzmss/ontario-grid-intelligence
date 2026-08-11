"""
Weather Extractor (Open-Meteo API)

Pulls hourly weather data for Toronto from Open-Meteo's free API.
Temperature is the #1 driver of electricity demand — critical
for ML price/demand forecasting.

Source: https://open-meteo.com/ (free, no API key required)
Location: Toronto (43.65°N, 79.38°W)
"""

import pandas as pd
from datetime import datetime, timedelta
from etl.base_extractor import BaseExtractor


class WeatherExtractor(BaseExtractor):
    """Extracts hourly weather data from Open-Meteo."""

    EXPECTED_COLUMNS = ["date", "hour", "temperature_c"]

    def __init__(self):
        super().__init__(name="WeatherExtractor")
        self.api_url = "https://archive-api.open-meteo.com/v1/archive"
        self.lat = 43.65  # Toronto
        self.lon = -79.38

    def _fetch_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch weather data for a date range from Open-Meteo."""
        url = (
            f"{self.api_url}?"
            f"latitude={self.lat}&longitude={self.lon}"
            f"&start_date={start_date}&end_date={end_date}"
            f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
            f"&timezone=America/Toronto"
        )

        response = self.fetch_url(url)
        data = response.json()

        if "hourly" not in data:
            self.logger.warning(f"No hourly data in response for {start_date} to {end_date}")
            return pd.DataFrame()

        hourly = data["hourly"]
        df = pd.DataFrame({
            "datetime": hourly["time"],
            "temperature_c": hourly["temperature_2m"],
            "humidity_pct": hourly["relative_humidity_2m"],
            "wind_speed_kmh": hourly["wind_speed_10m"],
        })

        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.date
        df["hour"] = df["datetime"].dt.hour + 1  # Convert to 1-24 (IESO convention)
        df = df.drop(columns=["datetime"])

        self.logger.info(f"Weather {start_date} to {end_date}: {len(df)} rows extracted")
        return df

    def extract(self) -> pd.DataFrame:
        """Pull weather data for the current year up to yesterday."""
        now = datetime.now()
        start = f"{now.year}-01-01"
        # Open-Meteo archive goes up to ~2 days ago
        end = (now - timedelta(days=2)).strftime("%Y-%m-%d")

        df = self._fetch_range(start, end)
        self.validate(df, self.EXPECTED_COLUMNS)
        return df

    def extract_historical(self, start_year: int = 2024, end_year: int = 2026) -> pd.DataFrame:
        """Pull weather data for a range of years."""
        all_data = []
        now = datetime.now()

        for year in range(start_year, end_year + 1):
            start = f"{year}-01-01"
            if year == now.year:
                end = (now - timedelta(days=2)).strftime("%Y-%m-%d")
            else:
                end = f"{year}-12-31"

            df = self._fetch_range(start, end)
            if not df.empty:
                all_data.append(df)

        if not all_data:
            self.logger.warning("No weather data extracted")
            return pd.DataFrame()

        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "hour"], keep="last")
        combined = combined.sort_values(["date", "hour"]).reset_index(drop=True)

        self.logger.info(f"Historical weather: {len(combined)} total rows")
        return combined


if __name__ == "__main__":
    extractor = WeatherExtractor()
    df = extractor.run()
    print(f"\nExtracted {len(df)} rows of weather data")
    if not df.empty:
        print(df.head(10))
        print(f"\nTemp range: {df['temperature_c'].min()}°C to {df['temperature_c'].max()}°C")
