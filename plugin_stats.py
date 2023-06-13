from google.cloud import bigquery

# Construct a BigQuery client object.
client = bigquery.Client()


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


for pkg in ("nonebot2",):
    down = get_downloads_dry(pkg)
    print(f"{pkg}:", down)