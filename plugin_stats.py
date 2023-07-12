import sys
from google.cloud import bigquery
import requests

NoneBotPluginMeta = dict[
    {
        "module_name": str,
        "project_link": str,
        "name": str,
        "desc": str,
        "author": str,
        "homepage": str,
        "tags": list[dict[{"label": str, "color": str}]],
        "is_official": bool
    }
]

if sys.argv[1:]:
    print("*** Use local test list...")
    target_packages = sys.argv[1:]
else:
    print("*** Downloading plugins list...")
    data: list[NoneBotPluginMeta] = requests.get("https://registry.nonebot.dev/plugins.json").json()
    print("=== Downloaded plugins list")

    # Define the target packages and time interval
    target_packages = [x["project_link"] for x in data]

# Set up BigQuery client
client = bigquery.Client()
interval = 30  # Number of days for the time interval

# Construct the SQL query with placeholders
query = """
SELECT file.project AS package_name, COUNT(*) AS num_downloads
FROM `bigquery-public-data.pypi.file_downloads`
WHERE details.installer.name = 'pip'
    AND details.python != 'null'
    AND DATE(timestamp) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL @interval DAY) AND CURRENT_DATE()
    AND file.project IN UNNEST(@target_packages)
GROUP BY package_name
"""

# Define the query parameters
query_params = [
    bigquery.ArrayQueryParameter("target_packages", "STRING", target_packages),
    bigquery.ScalarQueryParameter("interval", "INT64", interval),
]

# Run the query with parameters
job_config = bigquery.QueryJobConfig(query_parameters=query_params)
query_job = client.query(query, job_config=job_config)

# Process the query results
for row in query_job:
    package_name = row['package_name']
    num_downloads = row['num_downloads']
    print(f"Package: {package_name}, Downloads: {num_downloads}")



def get_downloads_dry(pkg: str, interval: int = 30) -> int:
    results = client.query(
        f"""
        SELECT COUNT(*) AS num_downloads
        FROM `bigquery-public-data.pypi.file_downloads`
        WHERE file.project = {pkg!r}
            AND details.installer.name = 'pip'
            AND details.python != 'null'
        AND DATE(timestamp)
            BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {interval} DAY)
            AND CURRENT_DATE()
        """
    ).result()

    for row in results:
        return row["num_downloads"]
    
    raise RuntimeError(f"failed to get data of {pkg!r}")


def get_latest_upload_time(pkg: str):
    results = client.query(
        f"""
        SELECT MAX(upload_time) AS upload_time
        FROM `bigquery-public-data.pypi.distribution_metadata`
        WHERE name = {pkg!r}
        """
    ).result()

    for row in results:
        return row["upload_time"]
    
    raise RuntimeError(f"failed to get data of {pkg!r}")