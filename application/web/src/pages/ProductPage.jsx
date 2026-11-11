import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createOrder, getProduct } from "../api";

export default function ProductPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getProduct(id)
      .then(setProduct)
      .catch((err) => setError(err.message));
  }, [id]);

  async function onSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const order = await createOrder({
        product_id: Number(id),
        quantity: Number(quantity),
      });
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!product && !error) return <p className="muted">Loading product…</p>;
  if (!product) return <p className="error">{error}</p>;

  return (
    <section className="panel">
      <h1>{product.name}</h1>
      <p className="price">${Number(product.price).toFixed(2)}</p>
      <p className="muted">{product.stock} in stock</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="quantity">Quantity</label>
        <input
          id="quantity"
          type="number"
          min="1"
          max={product.stock}
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
        />
        <button type="submit" disabled={submitting || product.stock < 1}>
          {submitting ? "Placing order…" : "Place order"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
