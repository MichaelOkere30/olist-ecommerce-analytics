"""
Olist E-Commerce Analytics: Data Cleaning and SQL Load
======================================================
Pipeline: Jupyter Notebook (cleaning) -> PostgreSQL -> Power BI

Goal
----
Turn the nine raw Olist CSV files into clean, correctly typed tables and load
them into a PostgreSQL database so they are ready for SQL analysis and
Power BI reporting.

Usage
-----
    python 01_olist_data_cleaning_and_sql_load.py

Requirements
------------
    pip install pandas sqlalchemy psycopg2-binary
"""

import zipfile

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Boolean, DateTime, Float, Integer, Numeric, Text

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
ZIP_PATH = "archive (1).zip"
DB_NAME = "ecommerce_database"
DEFAULT_DB_URL = "postgresql+psycopg2://postgres@localhost:5432/postgres"
DB_URL = f"postgresql+psycopg2://postgres@localhost:5432/{DB_NAME}"

cleaned_tables = {}  # holds cleaned dataframes
sql_dtypes = {}      # holds explicit SQL column types per table


# --------------------------------------------------------------------------
# 1. Load raw data
# --------------------------------------------------------------------------
def load_raw_tables(zip_path):
    """Read every CSV inside the zip archive into a dict of dataframes."""
    tables = {}
    with zipfile.ZipFile(zip_path, "r") as z:
        for file_name in z.namelist():
            if file_name.endswith(".csv"):
                with z.open(file_name) as file:
                    tables[file_name] = pd.read_csv(file)
    print("Data loaded successfully! Here are your files:\n")
    print(tables.keys())
    return tables


# --------------------------------------------------------------------------
# 2. Clean each table
# --------------------------------------------------------------------------
def clean_customers(raw):
    customers = raw["olist_customers_dataset.csv"].copy()
    print("customers duplicates:", customers.duplicated().sum())

    customers["customer_id"] = customers["customer_id"].astype("string")
    customers["customer_unique_id"] = customers["customer_unique_id"].astype("string")
    customers["customer_zip_code_prefix"] = (
        customers["customer_zip_code_prefix"].astype("string").str.zfill(5)
    )
    customers["customer_city"] = customers["customer_city"].astype("string")
    customers["customer_state"] = customers["customer_state"].astype("string")

    sql_dtypes["customers"] = {
        "customer_id": Text, "customer_unique_id": Text,
        "customer_zip_code_prefix": Text,
        "customer_city": Text, "customer_state": Text,
    }
    cleaned_tables["customers"] = customers


def clean_geolocation(raw):
    geolocation = raw["olist_geolocation_dataset.csv"].copy()

    geolocation["geolocation_zip_code_prefix"] = (
        geolocation["geolocation_zip_code_prefix"].astype("string").str.zfill(5)
    )
    geolocation["geolocation_lat"] = geolocation["geolocation_lat"].astype("float64")
    geolocation["geolocation_lng"] = geolocation["geolocation_lng"].astype("float64")
    geolocation["geolocation_city"] = geolocation["geolocation_city"].astype("string")
    geolocation["geolocation_state"] = geolocation["geolocation_state"].astype("string")

    print("geolocation duplicates:", geolocation.duplicated().sum())

    # Raw file has ~1M rows with many rows per zip prefix.
    # Collapse to one row per zip prefix (average coordinates).
    geolocation = geolocation.drop_duplicates()
    geolocation = (
        geolocation
        .groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            geolocation_lat=("geolocation_lat", "mean"),
            geolocation_lng=("geolocation_lng", "mean"),
            geolocation_city=("geolocation_city", "first"),
            geolocation_state=("geolocation_state", "first"),
        )
    )
    assert geolocation["geolocation_zip_code_prefix"].is_unique

    sql_dtypes["geolocation"] = {
        "geolocation_zip_code_prefix": Text,
        "geolocation_lat": Float, "geolocation_lng": Float,
        "geolocation_city": Text, "geolocation_state": Text,
    }
    cleaned_tables["geolocation"] = geolocation


def clean_order_items(raw):
    order_items = raw["olist_order_items_dataset.csv"].copy()

    order_items["order_id"] = order_items["order_id"].astype("string")
    order_items["order_item_id"] = order_items["order_item_id"].astype("int8")
    order_items["product_id"] = order_items["product_id"].astype("string")
    order_items["seller_id"] = order_items["seller_id"].astype("string")
    order_items["shipping_limit_date"] = pd.to_datetime(order_items["shipping_limit_date"])
    order_items[["price", "freight_value"]] = (
        order_items[["price", "freight_value"]].round(2)
    )

    sql_dtypes["order_items"] = {
        "order_id": Text, "order_item_id": Integer,
        "product_id": Text, "seller_id": Text,
        "shipping_limit_date": DateTime,
        "price": Numeric(10, 2), "freight_value": Numeric(10, 2),
    }
    cleaned_tables["order_items"] = order_items


def clean_order_payments(raw):
    order_payment = raw["olist_order_payments_dataset.csv"].copy()
    print("payment types:\n", order_payment["payment_type"].value_counts())

    order_payment["order_id"] = order_payment["order_id"].astype("string")
    order_payment["payment_sequential"] = order_payment["payment_sequential"].astype("int8")
    order_payment["payment_type"] = order_payment["payment_type"].astype("category")
    order_payment["payment_installments"] = order_payment["payment_installments"].astype("int8")
    order_payment["payment_value"] = order_payment["payment_value"].round(2)

    sql_dtypes["order_payment"] = {
        "order_id": Text, "payment_sequential": Integer,
        "payment_type": Text, "payment_installments": Integer,
        "payment_value": Numeric(12, 2),
    }
    cleaned_tables["order_payment"] = order_payment


def clean_order_reviews(raw):
    order_reviews = raw["olist_order_reviews_dataset.csv"].copy()

    order_reviews["review_id"] = order_reviews["review_id"].astype("string")
    order_reviews["order_id"] = order_reviews["order_id"].astype("string")
    order_reviews["review_score"] = order_reviews["review_score"].astype("int8")
    order_reviews["review_comment_title"] = order_reviews["review_comment_title"].astype("string")
    order_reviews["review_comment_message"] = order_reviews["review_comment_message"].astype("string")
    order_reviews["review_creation_date"] = pd.to_datetime(order_reviews["review_creation_date"])
    order_reviews["review_answer_timestamp"] = pd.to_datetime(order_reviews["review_answer_timestamp"])

    # Most reviews have no title/comment. Fill so the text columns have no nulls.
    # NOTE: adjust the fill text to match whatever you used in your notebook.
    order_reviews["review_comment_title"] = order_reviews["review_comment_title"].fillna("No title")
    order_reviews["review_comment_message"] = order_reviews["review_comment_message"].fillna("No comment")

    sql_dtypes["order_reviews"] = {
        "review_id": Text, "order_id": Text, "review_score": Integer,
        "review_comment_title": Text, "review_comment_message": Text,
        "review_creation_date": DateTime, "review_answer_timestamp": DateTime,
    }
    cleaned_tables["order_reviews"] = order_reviews


def clean_orders(raw):
    orders = raw["olist_orders_dataset.csv"].copy()
    print("order status:\n", orders["order_status"].value_counts())

    orders["order_id"] = orders["order_id"].astype("string")
    orders["customer_id"] = orders["customer_id"].astype("string")
    orders["order_status"] = orders["order_status"].astype("category")

    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col])

    # Actual delivery time: purchase -> delivered to customer
    orders["delivery_time_days"] = (
        orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
    ).dt.days
    # Promised delivery time: purchase -> estimated delivery date at checkout
    orders["target_delivery_time_days"] = (
        orders["order_estimated_delivery_date"] - orders["order_purchase_timestamp"]
    ).dt.days

    # Nullable integers (orders not yet delivered stay NULL)
    orders["delivery_time_days"] = orders["delivery_time_days"].astype("Int16")
    orders["target_delivery_time_days"] = orders["target_delivery_time_days"].astype("Int16")

    orders["is_late"] = orders["delivery_time_days"] > orders["target_delivery_time_days"]
    print("is_late:\n", orders["is_late"].value_counts())

    sql_dtypes["orders"] = {
        "order_id": Text, "customer_id": Text, "order_status": Text,
        "order_purchase_timestamp": DateTime,
        "order_approved_at": DateTime,
        "order_delivered_carrier_date": DateTime,
        "order_delivered_customer_date": DateTime,
        "order_estimated_delivery_date": DateTime,
        "delivery_time_days": Integer, "target_delivery_time_days": Integer,
        "is_late": Boolean,
    }
    cleaned_tables["orders"] = orders


def clean_products_and_translation(raw):
    products = raw["olist_products_dataset.csv"].copy()
    translation = raw["product_category_name_translation.csv"].copy()

    # --- products ---
    products["product_category_name"] = products["product_category_name"].fillna("Unknown")
    products["product_id"] = products["product_id"].astype("string")
    products["product_category_name"] = products["product_category_name"].astype("string")
    products = products.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length",
    })

    # --- translation ---
    translation["product_category_name"] = translation["product_category_name"].astype("string")
    translation["product_category_name_english"] = translation["product_category_name_english"].astype("string")

    # Categories present in products but missing from the translation file
    missing = set(products["product_category_name"]) - set(translation["product_category_name"])
    print("Categories missing from translation:", missing)

    extra = pd.DataFrame({
        "product_category_name": [
            "portateis_cozinha_e_preparadores_de_alimentos", "pc_gamer", "Unknown",
        ],
        "product_category_name_english": [
            "portable_kitchen_food_preparers", "pc_gamer", "Unknown",
        ],
    }).astype("string")
    translation = pd.concat([translation, extra], ignore_index=True)

    # Add the English category name to products
    n_before = len(products)
    products = products.merge(translation, on="product_category_name", how="left")
    assert len(products) == n_before, "Merge changed the number of product rows"
    print("Missing English names:", products["product_category_name_english"].isna().sum())

    sql_dtypes["products"] = {
        "product_id": Text, "product_category_name": Text,
        "product_category_name_english": Text,
        "product_name_length": Float, "product_description_length": Float,
        "product_photos_qty": Float,
        "product_weight_g": Float, "product_length_cm": Float,
        "product_height_cm": Float, "product_width_cm": Float,
    }
    sql_dtypes["category_name_translation"] = {
        "product_category_name": Text, "product_category_name_english": Text,
    }
    cleaned_tables["products"] = products
    cleaned_tables["category_name_translation"] = translation


def clean_sellers(raw):
    sellers = raw["olist_sellers_dataset.csv"].copy()

    sellers["seller_id"] = sellers["seller_id"].astype("string")
    sellers["seller_zip_code_prefix"] = (
        sellers["seller_zip_code_prefix"].astype("string").str.zfill(5)
    )
    sellers["seller_city"] = sellers["seller_city"].astype("string")
    sellers["seller_state"] = sellers["seller_state"].astype("string")

    sql_dtypes["sellers"] = {
        "seller_id": Text, "seller_zip_code_prefix": Text,
        "seller_city": Text, "seller_state": Text,
    }
    cleaned_tables["sellers"] = sellers


# --------------------------------------------------------------------------
# 3. Push to PostgreSQL
# --------------------------------------------------------------------------
def create_database():
    """Create the target database if it does not exist yet."""
    default_engine = create_engine(DEFAULT_DB_URL, isolation_level="AUTOCOMMIT")
    with default_engine.connect() as conn:
        try:
            conn.execute(text(f"CREATE DATABASE {DB_NAME};"))
            print("Database created successfully!")
        except Exception as e:
            print("Database already exists or error:", e)


def push_to_sql():
    # Sanity check: every dtype key must be a real column
    for name, df in cleaned_tables.items():
        stray = set(sql_dtypes[name]) - set(df.columns)
        print(name, stray)  # should print set() for every table
        assert not stray, f"{name}: dtype keys not in dataframe: {stray}"

    create_database()
    engine = create_engine(DB_URL)
    for name, df in cleaned_tables.items():
        df.to_sql(
            name, engine, if_exists="replace", index=False,
            dtype=sql_dtypes[name], chunksize=50000,
        )
        print(f"Loaded {name}: {len(df):,} rows")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    raw_tables = load_raw_tables(ZIP_PATH)

    clean_customers(raw_tables)
    clean_geolocation(raw_tables)
    clean_order_items(raw_tables)
    clean_order_payments(raw_tables)
    clean_order_reviews(raw_tables)
    clean_orders(raw_tables)
    clean_products_and_translation(raw_tables)
    clean_sellers(raw_tables)

    push_to_sql()


if __name__ == "__main__":
    main()
