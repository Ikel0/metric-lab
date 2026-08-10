#!/usr/bin/env python3
"""Metric Lab: a small but real CSV-to-mart analytics pipeline."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "warehouse.db"

def load_csv(name):
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def build(db_path=DB_PATH):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.executescript("""
      DROP TABLE IF EXISTS dim_customers; DROP TABLE IF EXISTS dim_products; DROP TABLE IF EXISTS fact_orders; DROP TABLE IF EXISTS mart_daily_revenue;
      CREATE TABLE dim_customers(customer_id TEXT PRIMARY KEY, segment TEXT, city TEXT);
      CREATE TABLE dim_products(product_id TEXT PRIMARY KEY, product_name TEXT, category TEXT, unit_price REAL);
      CREATE TABLE fact_orders(order_id TEXT PRIMARY KEY, order_date TEXT, customer_id TEXT, product_id TEXT, quantity INTEGER, revenue REAL);
    """)
    cursor.executemany("INSERT INTO dim_customers VALUES (:customer_id,:segment,:city)", load_csv("customers.csv"))
    cursor.executemany("INSERT INTO dim_products VALUES (:product_id,:product_name,:category,:unit_price)", load_csv("products.csv"))
    rows = []
    prices = {row[0]:row[1] for row in cursor.execute("SELECT product_id,unit_price FROM dim_products")}
    for order in load_csv("orders.csv"):
        rows.append((order["order_id"],order["order_date"],order["customer_id"],order["product_id"],int(order["quantity"]),int(order["quantity"])*prices[order["product_id"]]))
    cursor.executemany("INSERT INTO fact_orders VALUES (?,?,?,?,?,?)", rows)
    cursor.execute("""CREATE TABLE mart_daily_revenue AS SELECT order_date, COUNT(*) AS orders, ROUND(SUM(revenue),2) AS revenue, ROUND(AVG(revenue),2) AS avg_order_value FROM fact_orders GROUP BY order_date ORDER BY order_date""")
    connection.commit(); connection.close()
    return {"orders":len(rows),"customers":len(load_csv("customers.csv")),"database":str(db_path)}

def metrics(db_path=DB_PATH):
    if not db_path.exists(): build(db_path)
    connection = sqlite3.connect(db_path); connection.row_factory = sqlite3.Row; cursor = connection.cursor()
    total = cursor.execute("SELECT COUNT(*) orders, ROUND(SUM(revenue),2) revenue, ROUND(AVG(revenue),2) aov FROM fact_orders").fetchone()
    daily = [dict(row) for row in cursor.execute("SELECT * FROM mart_daily_revenue")]
    by_category = [dict(row) for row in cursor.execute("SELECT p.category, ROUND(SUM(f.revenue),2) revenue FROM fact_orders f JOIN dim_products p USING(product_id) GROUP BY 1 ORDER BY 2 DESC")]
    connection.close(); return {"summary":dict(total),"daily":daily,"categories":by_category}

if __name__ == "__main__": print(build())
