from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import bigquery
import requests

NoneBotMeta = dict[
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

# Construct a BigQuery client object.
client = bigquery.Client()

print("*** Downloading plugins list...")
data: list[NoneBotMeta] = requests.get("https://v2.nonebot.dev/plugins.json").json()
print("=== Downloaded plugins list")


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


def get_plugin_list() -> list[str]:
    return [x["project_link"] for x in data]


downloads: list[tuple[str, int]] = []


def get_and_store(pkg: str):
    downloads.append((pkg, get_downloads_dry(pkg)))


with ThreadPoolExecutor(max_workers=8) as exc:
    tasks = [exc.submit(get_and_store, pkg) for pkg in get_plugin_list()]
    co = 0
    for _ in as_completed(tasks):
        print(f"=== {co := co + 1}/{len(data)} done")


downloads.sort(key=lambda x: x[1], reverse=True)
for pkg, down in downloads:
    print(f"{pkg}:", down)