# test-nonebot-packages-stats

Test repository for nonebot2 plugins stats.

## Data source

This repo gets data from Google BigQuery.

## Base data

Base data are stored in [statistics.json](./statistics.json).

Data structure:

```plaintext
{
    "{package_standard_name}": {
        // {package_standard_name} is in lower case
        // and only uses '-' for splitting words.
        "day7": int,  // downloads in 7 days
        "day30": int,  // downloads in 30 days
        "lastup": timestamp  // package last update time
    }
}
```

## Ranking

The python script includes a ranking formula for ranking and sorting data
for terminal output. The formula is very rough and cannot be used for good
ranking for now.

The ranking formula generally uses downloads and last-update time. Downloads
in 7 days are more powerful than 30 days, and newer packages are more likely
to have a higher ranking score.

## Is it accurate?

This project cannot guarantee any accuracy for several complex reasons:

- Download numbers are easy to be cheated. For this we tried to except suspicious data such as unknown version and installer;
- Downloads from mirror sites are not included.

