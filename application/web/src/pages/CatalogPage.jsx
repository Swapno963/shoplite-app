import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProducts } from "../api";

export default function CatalogPage() {
  const [products, setProducts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listProducts()
      .then(setProducts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading catalog…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <h1>Catalog</h1>
      <p className="muted">Browse products and place an order.</p>
      <div className="grid">
        {products.map((product) => (
          <Link key={product.id} to={`/products/${product.id}`} className="card">
            <h2>{product.name}</h2>
            <p className="price">${Number(product.price).toFixed(2)}</p>
            <p className="muted">{product.stock} in stock</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
