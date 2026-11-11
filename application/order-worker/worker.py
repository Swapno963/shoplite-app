import json
import logging
import os
import random
import signal
import time
from datetime import datetime, timezone

import psycopg
import redis

from logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("order-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ORDERS_QUEUE = os.getenv("ORDERS_QUEUE", "orders:pending")
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "shoplite"),
        password=os.getenv("POSTGRES_PASSWORD", "shoplite"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "shoplite"),
    ),
)
CHAOS_MEMORY_LEAK = os.getenv("CHAOS_MEMORY_LEAK", "false").lower() in ("1", "true", "yes")
CHAOS_SLOW_DB = os.getenv("CHAOS_SLOW_DB", "false").lower() in ("1", "true", "yes")
PROCESS_MIN_SECONDS = float(os.getenv("PROCESS_MIN_SECONDS", "1"))
PROCESS_MAX_SECONDS = float(os.getenv("PROCESS_MAX_SECONDS", "2"))

shutdown_requested = False
leaked_orders: list[dict] = []


def handle_signal(signum, _frame):
    global shutdown_requested
    logger.info("received signal %s; finishing current work then exiting", signum)
    shutdown_requested = True


def connect_db():
    return psycopg.connect(POSTGRES_DSN, autocommit=True)


def maybe_slow_db(conn, order_id: int) -> None:
    if CHAOS_SLOW_DB:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_sleep(2)")
            logger.info("chaos slow db injected for order %s", order_id)


def update_order(conn, order_id: int, status: str, completed_at=None) -> None:
    maybe_slow_db(conn, order_id)
    with conn.cursor() as cur:
        if completed_at is None:
            cur.execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                (status, order_id),
            )
        else:
            cur.execute(
                "UPDATE orders SET status = %s, completed_at = %s WHERE id = %s",
                (status, completed_at, order_id),
            )


def fetch_order(conn, order_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.id, o.product_id, o.quantity, o.status, p.stock
            FROM orders o
            JOIN products p ON p.id = o.product_id
            WHERE o.id = %s
            """,
            (order_id,),
        )
        return cur.fetchone()


def decrement_stock(conn, product_id: int, quantity: int, order_id: int) -> int:
    maybe_slow_db(conn, order_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s AND stock >= %s
            RETURNING stock
            """,
            (quantity, product_id, quantity),
        )
        row = cur.fetchone()
        return row[0] if row else -1


def process_order(conn, payload: dict) -> None:
    order_id = payload["order_id"]
    extra = {"trace_id": str(order_id)}
    logger.info("processing order %s", order_id, extra=extra)

    row = fetch_order(conn, order_id)
    if row is None:
        logger.warning("order %s not found", order_id, extra=extra)
        return

    _id, product_id, quantity, status, _stock = row
    if status != "PENDING":
        logger.info("skipping order %s with status %s", order_id, status, extra=extra)
        return

    update_order(conn, order_id, "PROCESSING")
    time.sleep(random.uniform(PROCESS_MIN_SECONDS, PROCESS_MAX_SECONDS))

    remaining = decrement_stock(conn, product_id, quantity, order_id)
    completed_at = datetime.now(timezone.utc)
    if remaining < 0:
        update_order(conn, order_id, "FAILED", completed_at)
        logger.warning("order %s failed: insufficient stock", order_id, extra=extra)
        final_status = "FAILED"
    else:
        update_order(conn, order_id, "COMPLETED", completed_at)
        logger.info("order %s completed", order_id, extra=extra)
        final_status = "COMPLETED"

    if CHAOS_MEMORY_LEAK:
        leaked_orders.append({"order_id": order_id, "status": final_status, "blob": "x" * 1024})


def wait_for_dependencies(redis_client) -> None:
    while not shutdown_requested:
        try:
            redis_client.ping()
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            logger.info("database and queue are reachable")
            return
        except Exception:
            logger.exception("waiting for database and queue")
            time.sleep(2)


def main() -> None:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    wait_for_dependencies(redis_client)
    logger.info("order-worker started; listening on %s", ORDERS_QUEUE)

    conn = connect_db()
    try:
        while not shutdown_requested:
            item = redis_client.blpop(ORDERS_QUEUE, timeout=1)
            if item is None:
                continue
            _queue, raw = item
            try:
                payload = json.loads(raw)
                process_order(conn, payload)
            except Exception:
                logger.exception("failed to process message: %s", raw)
    finally:
        conn.close()
        logger.info("order-worker stopped")


if __name__ == "__main__":
    main()
