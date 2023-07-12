from datetime import datetime
import json
import sys
from time import time
from typing import Literal, cast
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
    target_packages = [x["project_link"].replace("_", "-") for x in data]


def standname(name: str):
    """Convert name to valid PyPI name"""
    return name.lower()


results: dict[str, dict[{"down7": int, "down30": int, "lastup": int}]] = {
    standname(pkg): {"down7": 0, "down30": 0, "lastup": 0} for pkg in target_packages
}

# Set up BigQuery client
client = bigquery.Client()


def get_downloads(interval: Literal[7, 30] = 30) -> None:
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
        bigquery.ArrayQueryParameter(
            "target_packages", "STRING", 
            [standname(x) for x in target_packages]
            # here needs to input standard name
        ),
        bigquery.ScalarQueryParameter("interval", "INT64", interval),
    ]

    # Run the query with parameters
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = client.query(query, job_config=job_config)

    # Process the query results
    for row in query_job:
        package_name = row['package_name']
        num_downloads = row['num_downloads']
        results[package_name][f"down{interval}"] = num_downloads


def get_latest_upload_time():
    # Define the query parameters
    query_params = [
        bigquery.ArrayQueryParameter("target_packages", "STRING", target_packages)
    ]
    # Run the query with parameters
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)

    qjob = client.query(
        """
        SELECT name, MAX(upload_time) AS upload_time
        FROM `bigquery-public-data.pypi.distribution_metadata`
        WHERE name IN UNNEST(@target_packages)
        GROUP BY name
        """, job_config=job_config
    )

    for row in qjob:
        package_name = standname(row['name'])
        # here needs to output standard name
        upload_time = row['upload_time']
        results[package_name]["lastup"] = int(cast("datetime", upload_time).timestamp())


gtime = time()


def get_ranking_key(name: str, stat: dict[{"down7": int, "down30": int, "lastup": int}]):
    return 10000 * (cast(float, stat["down7"] ** 1.45) + stat["down30"]) / max(24 * 60 * 60, gtime - stat["lastup"]), name


try:
    for n in (7, 30):
        get_downloads(n)
    get_latest_upload_time()

    with open("statistics.json", "w") as f:
        json.dump(results, f, indent=4)
finally:
    sorted_res = sorted(
        results.items(),
        key=lambda x: get_ranking_key(*x),
        reverse=True
    )
    print(
        "{n:<42}{d7:>8}{d30:>8}  {u:<22} {rk:>10}".format(
            n="Name", d7="7day", d30="30day", u="Last Update", rk="Ranking"
        )
    )
    for n, d in sorted_res:
        d7, d30 = d["down7"], d["down30"]
        rk = get_ranking_key(n, d)[0]
        u = datetime.fromtimestamp(d["lastup"]).isoformat()
        print(f"{n:<42}{d7:8}{d30:8}  {u:<22} {rk:10.5}")