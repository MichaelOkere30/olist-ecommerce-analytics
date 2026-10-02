-- DimDate
CREATE OR REPLACE VIEW dim_date AS
WITH date_series AS (
	SELECT generate_series(
		'2016-01-01'::date,
		'2020-12-31'::date,
		'1 day'::interval
	)::date AS date_day
)
SELECT
	TO_CHAR(date_day, 'YYYYMMDD')::integer			AS date_key, 
	date_day										AS full_date,
	EXTRACT(YEAR FROM date_day)::integer			AS year,
	EXTRACT(QUARTER FROM date_day)::integer			AS quarter,
	EXTRACT(MONTH FROM date_day):: integer			AS month,
	TO_CHAR(date_day, 'Month')						AS month_name,
	EXTRACT(WEEK FROM date_day)::integer			AS week_of_year, 
	EXTRACT(DOW FROM date_day)::integer				AS day_of_week,
	TO_CHAR(date_day, 'Day')						AS day_name,
	CASE WHEN EXTRACT (DOW FROM date_day) IN (0, 6) THEN TRUE ELSE FALSE END AS
	is_weekend,
	TO_CHAR(date_day, 'YYYY-"Q"Q')					AS year_quarter, 
	TO_CHAR(date_day, 'YYYY-MM')					AS year_month
FROM date_series;

