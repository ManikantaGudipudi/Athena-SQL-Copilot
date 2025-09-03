SYSTEM = (
    "You are an analytics SQL assistant for Amazon Athena (Trino/Presto dialect). "
    "Return ONLY ONE SQL statement. No explanations. No comments. No code fences. "
    "Use explicit column names (avoid SELECT *). "
    "Quote table names that start with a digit using double quotes. "
    "If partitions exist (year, month), filter them when appropriate."
)

FEWSHOTS = """
Tables:
- lookup(columns=[locationid, borough, zone, service_zone])
- "2019"(columns=[tpep_pickup_datetime, tpep_dropoff_datetime, passenger_count, trip_distance, payment_type, pulocationid, dolocationid, fare_amount, total_amount])

Q: Show 5 rows from lookup.
SQL:
SELECT locationid, borough, zone, service_zone
FROM lookup
LIMIT 5;

Q: Count trips per payment type.
SQL:
SELECT payment_type, COUNT(*) AS trips
FROM "2019"
GROUP BY payment_type
ORDER BY trips DESC;

Q: Daily trips for January 2019 (first 10 days), ordered by day.
SQL:
SELECT date(tpep_pickup_datetime) AS day, COUNT(*) AS trips
FROM "2019"
WHERE date(tpep_pickup_datetime) BETWEEN DATE '2019-01-01' AND DATE '2019-01-10'
GROUP BY day
ORDER BY day;
""".strip()
