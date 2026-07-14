import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

const storage = {
  get access() { return localStorage.getItem("td_access"); },
  get refresh() { return localStorage.getItem("td_refresh"); },
  set(tokens) {
    localStorage.setItem("td_access", tokens.access_token);
    localStorage.setItem("td_refresh", tokens.refresh_token);
  },
  clear() {
    localStorage.removeItem("td_access");
    localStorage.removeItem("td_refresh");
  },
};

export { storage as tokenStorage };

api.interceptors.request.use((config) => {
  const token = storage.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes("/api/auth/");
    if (error.response?.status === 401 && !original._retried && !isAuthCall && storage.refresh) {
      original._retried = true;
      try {
        refreshPromise ??= axios
          .post(`${API_URL}/api/auth/refresh`, { refresh_token: storage.refresh })
          .finally(() => { refreshPromise = null; });
        const { data } = await refreshPromise;
        storage.set(data);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        storage.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function apiErrorMessage(error) {
  return error.response?.data?.detail || error.message || "Something went wrong";
}
