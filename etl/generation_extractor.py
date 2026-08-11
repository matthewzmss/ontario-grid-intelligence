"""
IESO Generation by Fuel Type Extractor

Pulls hourly generation data broken down by fuel type from IESO.
Source: https://reports-public.ieso.ca/public/GenOutputbyFuelHourly/

Data is in XML format with yearly files (~6.8MB each).
Fuel types: Nuclear, Gas, Hydro, Wind, Solar, Biofuel

Uses streaming XML parsing (iterparse) to handle large files
without loading the entire DOM into memory.
"""

import pandas as pd
from lxml import etree
from io import BytesIO
from etl.base_extractor import BaseExtractor


class GenerationExtractor(BaseExtractor):
    """Extracts hourly generation by fuel type from IESO XML feeds."""

    EXPECTED_COLUMNS = ["date", "hour", "fuel_type", "output_mw"]

    def __init__(self):
        super().__init__(name="GenerationExtractor")
        self.endpoint = f"{self.base_url}/GenOutputbyFuelHourly"

    def _parse_generation_xml(self, xml_content: bytes) -> pd.DataFrame:
        """
        Parse IESO generation XML file.

        Actual XML structure:
        <Document xmlns="http://www.ieso.ca/schema">
          <DocBody>
            <DailyData>
              <Day>2026-01-01</Day>
              <HourlyData>
                <Hour>1</Hour>
                <FuelTotal>
                  <Fuel>NUCLEAR</Fuel>
                  <EnergyValue>
                    <Output>9602</Output>
                  </EnergyValue>
                </FuelTotal>
              </HourlyData>
            </DailyData>
          </DocBody>
        </Document>
        """
        records = []

        try:
            tree = etree.parse(BytesIO(xml_content))
            root = tree.getroot()
            ns = "{http://www.ieso.ca/schema}"

            for daily in root.iter(f"{ns}DailyData"):
                day_elem = daily.find(f"{ns}Day")
                if day_elem is None:
                    continue
                day = day_elem.text

                for hourly in daily.findall(f"{ns}HourlyData"):
                    hour_elem = hourly.find(f"{ns}Hour")
                    if hour_elem is None:
                        continue
                    hour = int(hour_elem.text)

                    for fuel_total in hourly.findall(f"{ns}FuelTotal"):
                        fuel_elem = fuel_total.find(f"{ns}Fuel")
                        energy_value = fuel_total.find(f"{ns}EnergyValue")

                        if fuel_elem is not None and energy_value is not None:
                            output_elem = energy_value.find(f"{ns}Output")
                            if output_elem is not None and output_elem.text:
                                records.append({
                                    "date": day,
                                    "hour": hour,
                                    "fuel_type": fuel_elem.text.strip().title(),
                                    "output_mw": float(output_elem.text),
                                })

        except etree.XMLSyntaxError as e:
            self.logger.error(f"XML parsing error: {e}")
            raise

        df = pd.DataFrame(records)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        return df

    def extract(self) -> pd.DataFrame:
        """Pull current year generation data."""
        url = f"{self.endpoint}/PUB_GenOutputbyFuelHourly.xml"
        response = self.fetch_url(url)
        df = self._parse_generation_xml(response.content)
        self.validate(df, self.EXPECTED_COLUMNS)
        return df

    def extract_year(self, year: int) -> pd.DataFrame:
        """Pull generation data for a specific year."""
        url = f"{self.endpoint}/PUB_GenOutputbyFuelHourly_{year}.xml"
        self.logger.info(f"Extracting generation for year {year}")

        try:
            response = self.fetch_url(url)
        except Exception:
            self.logger.warning(f"No generation data available for year {year}")
            return pd.DataFrame()

        df = self._parse_generation_xml(response.content)
        self.logger.info(f"Year {year}: {len(df)} rows extracted")
        return df

    def extract_historical(self, start_year: int = 2020, end_year: int = 2026) -> pd.DataFrame:
        """Pull generation data for multiple years."""
        all_data = []

        for year in range(start_year, end_year + 1):
            df = self.extract_year(year)
            if not df.empty:
                all_data.append(df)

        if not all_data:
            raise ValueError("No historical generation data could be extracted")

        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "hour", "fuel_type"], keep="last")
        combined = combined.sort_values(["date", "hour", "fuel_type"]).reset_index(drop=True)

        self.logger.info(f"Historical extraction complete: {len(combined)} total rows")
        return combined


if __name__ == "__main__":
    extractor = GenerationExtractor()
    df = extractor.run()
    print(f"\nExtracted {len(df)} rows of generation data")
    print(f"\nFuel types found: {df['fuel_type'].unique()}")
    print(df.head(20))
