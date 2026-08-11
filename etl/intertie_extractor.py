"""
IESO Intertie Flow Extractor

Pulls import/export electricity flow data between Ontario and
neighboring jurisdictions (Michigan, New York, Quebec, Manitoba).
Source: https://reports-public.ieso.ca/public/IntertieScheduleFlow/

XML structure:
  IMODocument > IMODocBody > Date (single date for entire file)
  IMODocBody > IntertieZone > IntertieZoneName + Schedules > Schedule > Hour, Import, Export
"""

import pandas as pd
from lxml import etree
from io import BytesIO
from etl.base_extractor import BaseExtractor


class IntertieExtractor(BaseExtractor):
    """Extracts intertie schedule and flow data from IESO."""

    def __init__(self):
        super().__init__(name="IntertieExtractor")
        self.endpoint = f"{self.base_url}/IntertieScheduleFlow"

    def extract(self) -> pd.DataFrame:
        """Pull current intertie schedule and flow data."""
        url = f"{self.endpoint}/PUB_IntertieScheduleFlow.xml"

        try:
            response = self.fetch_url(url)
        except Exception:
            self.logger.warning("Could not fetch intertie data")
            return pd.DataFrame()

        records = []
        tree = etree.parse(BytesIO(response.content))
        root = tree.getroot()
        ns = "{http://www.theIMO.com/schema}"

        # Date is at IMODocBody level (one date per file)
        body = root.find(f"{ns}IMODocBody")
        date_elem = body.find(f"{ns}Date") if body is not None else None
        report_date = date_elem.text.strip() if date_elem is not None else None

        if report_date is None:
            self.logger.warning("No date found in intertie XML")
            return pd.DataFrame()

        # Each IntertieZone has Schedules and possibly Actuals
        for iz in root.iter(f"{ns}IntertieZone"):
            zone_name_elem = iz.find(f"{ns}IntertieZoneName")
            if zone_name_elem is None:
                continue
            zone_name = zone_name_elem.text.strip()

            # Get scheduled imports/exports
            for schedules in iz.findall(f"{ns}Schedules"):
                for schedule in schedules.findall(f"{ns}Schedule"):
                    hour_elem = schedule.find(f"{ns}Hour")
                    import_elem = schedule.find(f"{ns}Import")
                    export_elem = schedule.find(f"{ns}Export")

                    if hour_elem is not None:
                        records.append({
                            "date": report_date,
                            "hour": int(hour_elem.text),
                            "intertie_zone": zone_name,
                            "schedule_import_mw": float(import_elem.text) if import_elem is not None and import_elem.text else 0,
                            "schedule_export_mw": float(export_elem.text) if export_elem is not None and export_elem.text else 0,
                        })

            # Get actual flows if available
            for actuals in iz.findall(f"{ns}Actuals"):
                for actual in actuals.findall(f"{ns}Actual"):
                    hour_elem = actual.find(f"{ns}Hour")
                    flow_elem = actual.find(f"{ns}Flow")

                    if hour_elem is not None and flow_elem is not None:
                        hour = int(hour_elem.text)
                        # Update existing record with actual flow
                        for rec in records:
                            if rec["date"] == report_date and rec["hour"] == hour and rec["intertie_zone"] == zone_name:
                                rec["actual_flow_mw"] = float(flow_elem.text) if flow_elem.text else None
                                break

        df = pd.DataFrame(records)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        self.logger.info(f"Intertie flows: {len(df)} rows extracted")
        return df


if __name__ == "__main__":
    extractor = IntertieExtractor()
    df = extractor.run()
    print(f"\nExtracted {len(df)} rows of intertie data")
    if not df.empty:
        print(f"Zones found: {df['intertie_zone'].unique()}")
        print(df.head(20))
