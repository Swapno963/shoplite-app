const API_BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

export const listProducts = () => request("/products");
export const getProduct = (id) => request(`/products/${id}`);
export const createOrder = (payload) =>
  request("/orders", { method: "POST", body: JSON.stringify(payload) });
export const getOrder = (id) => request(`/orders/${id}`);
