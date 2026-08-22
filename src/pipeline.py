#!/usr/bin/env python3
"""Metric Lab: quality-gated CSV to dimensional mart pipeline."""
from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "warehouse.db"
EXPECTED_COLUMNS = {
    "customers": {"customer_id", "segment", "city"},
    "products": {"product_id", "product_name", "category", "unit_price"},
    "orders": {"order_id", "order_date", "customer_id", "product_id", "quantity"},
}


class SourceValidationError(ValueError):
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        super().__init__("Source quality gate failed")


def load_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_sources() -> dict[str, list[dict[str, str]]]:
    return {
        "customers": load_csv("customers.csv"),
        "products": load_csv("products.csv"),
        "orders": load_csv("orders.csv"),
    }


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "passed" if passed else "failed", "detail": detail}


def quality_report(sources: dict[str, list[dict[str, str]]] | None = None) -> dict[str, Any]:
    sources = sources or load_sources()
    checks: list[dict[str, Any]] = []
    for name, columns in EXPECTED_COLUMNS.items():
        actual = set(sources[name][0]) if sources[name] else set()
        missing = sorted(columns - actual)
        checks.append(_check(f"{name}_schema", not missing, "schema expected" if not missing else f"missing: {', '.join(missing)}"))

    customers, products, orders = sources["customers"], sources["products"], sources["orders"]
    customer_ids = [row.get("customer_id", "") for row in customers]
    product_ids = [row.get("product_id", "") for row in products]
    order_ids = [row.get("order_id", "") for row in orders]
    checks.extend(
        [
            _check("customer_id_unique", len(customer_ids) == len(set(customer_ids)), "customer identifiers are unique"),
            _check("product_id_unique", len(product_ids) == len(set(product_ids)), "product identifiers are unique"),
            _check("order_id_unique", len(order_ids) == len(set(order_ids)), "order identifiers are unique"),
            _check("order_customer_fk", all(row.get("customer_id") in set(customer_ids) for row in orders), "all orders reference a known customer"),
            _check("order_product_fk", all(row.get("product_id") in set(product_ids) for row in orders), "all orders reference a known product"),
        ]
    )
    try:
        checks.append(_check("product_price_positive", all(float(row["unit_price"]) > 0 for row in products), "unit prices are positive"))
    except (KeyError, ValueError):
        checks.append(_check("product_price_positive", False, "unit prices are numeric and positive"))
    try:
        checks.append(_check("order_quantity_positive", all(int(row["quantity"]) > 0 for row in orders), "quantities are positive integers"))
    except (KeyError, ValueError):
        checks.append(_check("order_quantity_positive", False, "quantities are positive integers"))
    try:
        for row in orders:
            datetime.strptime(row["order_date"], "%Y-%m-%d")
        checks.append(_check("order_date_iso", True, "order dates use YYYY-MM-DD"))
    except (KeyError, ValueError):
        checks.append(_check("order_date_iso", False, "order dates use YYYY-MM-DD"))

    fingerprint = hashlib.sha256(json.dumps(sources, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return {
        "status": "passed" if all(check["status"] == "passed" for check in checks) else "failed",
        "checks": checks,
        "rows": {name: len(rows) for name, rows in sources.items()},
        "source_fingerprint": fingerprint,
    }


def build(db_path: Path = DB_PATH) -> dict[str, Any]:
    sources = load_sources()
    quality = quality_report(sources)
    if quality["status"] != "passed":
        raise SourceValidationError(quality)
    customers, products, orders = sources["customers"], sources["products"], sources["orders"]
    run_at = datetime.now(UTC).isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            DROP TABLE IF EXISTS dim_customers;
            DROP TABLE IF EXISTS dim_products;
            DROP TABLE IF EXISTS fact_orders;
            DROP TABLE IF EXISTS mart_daily_revenue;
            DROP TABLE IF EXISTS pipeline_runs;
            CREATE TABLE dim_customers(customer_id TEXT PRIMARY KEY, segment TEXT, city TEXT);
            CREATE TABLE dim_products(product_id TEXT PRIMARY KEY, product_name TEXT, category TEXT, unit_price REAL);
            CREATE TABLE fact_orders(order_id TEXT PRIMARY KEY, order_date TEXT, customer_id TEXT, product_id TEXT, quantity INTEGER, revenue REAL);
            CREATE TABLE pipeline_runs(run_at TEXT NOT NULL, source_fingerprint TEXT NOT NULL, quality_status TEXT NOT NULL, quality_checks INTEGER NOT NULL);
            """
        )
        cursor.executemany("INSERT INTO dim_customers VALUES (:customer_id,:segment,:city)", customers)
        cursor.executemany("INSERT INTO dim_products VALUES (:product_id,:product_name,:category,:unit_price)", products)
        prices = {row[0]: row[1] for row in cursor.execute("SELECT product_id, unit_price FROM dim_products")}
        facts = [
            (row["order_id"], row["order_date"], row["customer_id"], row["product_id"], int(row["quantity"]), int(row["quantity"]) * prices[row["product_id"]])
            for row in orders
        ]
        cursor.executemany("INSERT INTO fact_orders VALUES (?,?,?,?,?,?)", facts)
        cursor.execute(
            """
            CREATE TABLE mart_daily_revenue AS
            SELECT order_date, COUNT(*) AS orders, ROUND(SUM(revenue),2) AS revenue, ROUND(AVG(revenue),2) AS avg_order_value
            FROM fact_orders GROUP BY order_date ORDER BY order_date
            """
        )
        cursor.execute(
            "INSERT INTO pipeline_runs VALUES (?, ?, ?, ?)",
            (run_at, quality["source_fingerprint"], quality["status"], len(quality["checks"])),
        )
    return {"orders": len(facts), "customers": len(customers), "database": str(db_path), "quality": quality}


def metrics(db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        build(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        total = cursor.execute("SELECT COUNT(*) orders, ROUND(SUM(revenue),2) revenue, ROUND(AVG(revenue),2) aov FROM fact_orders").fetchone()
        daily = [dict(row) for row in cursor.execute("SELECT * FROM mart_daily_revenue")]
        categories = [dict(row) for row in cursor.execute("SELECT p.category, ROUND(SUM(f.revenue),2) revenue FROM fact_orders f JOIN dim_products p USING(product_id) GROUP BY 1 ORDER BY 2 DESC")]
        run = cursor.execute("SELECT * FROM pipeline_runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return {"summary": dict(total), "daily": daily, "categories": categories, "lineage": dict(run) if run else None}


if __name__ == "__main__":
    print(build())
