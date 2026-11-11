import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getOrder } from "../api";

const TERMINAL = new Set(["COMPLETED", "FAILED"]);

export default function OrderPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function poll() {
      try {
        const data = await getOrder(id);
        if (cancelled) return;
        setOrder(data);
        if (!TERMINAL.has(data.status)) {
          timer = setTimeout(poll, 1500);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (error) return <p className="error">{error}</p>;
  if (!order) return <p className="muted">Loading order…</p>;

  return (
    <section className="panel">
      <h1>Order #{order.id}</h1>
      <p>
        Status: <strong className={`status ${order.status.toLowerCase()}`}>{order.status}</strong>
      </p>
      <p className="muted">Product #{order.product_id} · Quantity {order.quantity}</p>
      <Link to="/">Back to catalog</Link>
    </section>
  );
}
