import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import CatalogPage from "./pages/CatalogPage";
import ProductPage from "./pages/ProductPage";
import OrderPage from "./pages/OrderPage";

export default function App() {
  const location = useLocation();

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          ShopLite
        </Link>
        <nav>
          <Link className={location.pathname === "/" ? "active" : ""} to="/">
            Catalog
          </Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/products/:id" element={<ProductPage />} />
          <Route path="/orders/:id" element={<OrderPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
