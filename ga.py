#! /usr/bin/env python3
# -*- coding: utf-8

"""Google Analytics 4 Data API."""

import json
import os
import re
from collections import OrderedDict

import pycountry
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)

try:
    from BeautifulSoup import BeautifulSoup, NavigableString
except ImportError:
    from bs4 import BeautifulSoup, NavigableString

# --- CONFIGURATION ---
KEY_FILE_LOCATION = "ga.config"  # Path to your Service Account JSON
PROPERTY_ID = "368625663"  # REPLACE THIS (e.g., '123456789')
PATH_TO_POSTS = "./posts/"
# ---------------------

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_FILE_LOCATION
html_names = list(filter(lambda x: x[-5:] == ".html", (os.listdir(PATH_TO_POSTS))))


def initialize_analytics_data():
    """Initializes the GA4 Data Client."""
    return BetaAnalyticsDataClient()


def get_pageviews_report(client):
    """Queries GA4 for pageviews by page path."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date="2018-01-01", end_date="today")],
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True
            )
        ],
    )
    return client.run_report(request)


pageview_record = {}


def process_pageviews_response(response):
    """Parses the GA4 response and populates pageview_record."""
    print("Report result:")
    for row in response.rows:
        # GA4 returns pagePath as the first dimension
        raw_path = row.dimension_values[0].value
        pageviews = int(row.metric_values[0].value)

        # Regex logic to clean paths (kept from your original script)
        groups = re.search(r"/([^/]*?html)", raw_path)
        path = ""

        if groups:
            path = groups.group(1)
        else:
            if raw_path == "/" or raw_path == "":
                path = "index.html"
            else:
                # Handle edge cases where raw_path might not match
                path = raw_path

        path = path.replace("md.html", "html")

        # Accumulate pageviews
        pageview_record[path] = pageview_record.get(path, 0) + pageviews


def write_pageview_to_files():
    """Updates HTML files with pageview counts."""
    files_to_process = html_names + ["index.html", "about.html"]

    for html_name in files_to_process:
        print(f"generating pageview for {html_name}")

        # Determine correct file path
        full_path = PATH_TO_POSTS + html_name if html_name in html_names else html_name

        if not os.path.exists(full_path):
            print(f"Skipping {html_name}, file not found.")
            continue

        with open(full_path, "r", encoding="utf-8") as html_file:
            parsed_html = BeautifulSoup(
                html_file.read(), "html.parser"
            )  # Updated parser to html.parser or html5lib if installed

        pageview_span = parsed_html.find("span", attrs={"id": "pageviews"})

        if pageview_span:
            pageview_span.clear()
            count = pageview_record.get(html_name, 0)
            pageview_span.insert(
                0, NavigableString(f"This page has been viewed for {count} times")
            )

            with open(full_path, "w", encoding="utf-8") as html_file:
                html_file.write(str(parsed_html))
        else:
            print(f"No #pageviews span found in {html_name}")


def get_geo_report(client):
    """Queries GA4 for active users by country."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="country")],
        metrics=[
            Metric(name="activeUsers")
        ],  # 'users' in UA is usually 'activeUsers' or 'totalUsers' in GA4
        date_ranges=[DateRange(start_date="2018-01-01", end_date="today")],
    )
    return client.run_report(request)


geo_record = []


def process_geo_response(response):
    """Parses GA4 geo response."""
    countries_map = {}
    for country in pycountry.countries:
        countries_map[country.name] = country.alpha_3

    # Manual overrides (kept from your original script)
    countries_map.update(
        {
            "Russia": "RUS",
            "South Korea": "KOR",
            "Taiwan": "TWN",
            "Congo - Kinshasa": "COD",
            "Moldova": "MDA",
            "Vietnam": "VNM",
            "Myanmar (Burma)": "MMR",
            "Trinidad & Tobago": "TTO",
        }
    )

    historical_geo = OrderedDict()
    deprecated_path = "geo.json.deprecated"

    if os.path.exists(deprecated_path):
        try:
            with open(deprecated_path, "r", encoding="utf-8") as file_obj:
                previous_data = json.load(file_obj)

            for entry in previous_data:
                if not (isinstance(entry, (list, tuple)) and len(entry) == 2):
                    continue

                code, raw_value = entry
                try:
                    current_value = int(raw_value)
                except (TypeError, ValueError):
                    print(f"Skipping invalid historical entry for {code}: {raw_value}")
                    continue

                historical_geo[code] = historical_geo.get(code, 0) + current_value
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Failed to load {deprecated_path}: {exc}")

    print("Geo Report processing...")
    for row in response.rows:
        country_name = row.dimension_values[0].value
        metric_value = row.metric_values[0].value  # String value from GA4

        try:
            numeric_value = int(metric_value)
        except ValueError:
            print(f"Skipping invalid GA metric for {country_name}: {metric_value}")
            continue

        if country_name not in countries_map:
            print("!!!Unknown", country_name)

        country_code = countries_map.get(country_name, "Unknown")
        previous_total = historical_geo.get(country_code, 0)
        historical_geo[country_code] = previous_total + numeric_value

    print("Merged Geo Totals:")
    geo_record.clear()
    for code, value in historical_geo.items():
        print(f"{code}, {value}")
        geo_record.append([code, str(value)])


def main():
    client = initialize_analytics_data()

    # --- Pageviews ---
    print("Fetching Pageviews...")
    pv_response = get_pageviews_report(client)
    process_pageviews_response(pv_response)
    write_pageview_to_files()

    # --- Geo ---
    print("\nFetching Geo Data...")
    geo_response = get_geo_report(client)
    process_geo_response(geo_response)

    with open("geo.json", "w") as f:
        json.dump(geo_record, f, indent=2)


if __name__ == "__main__":
    main()
