import { createContext, useContext, useEffect, useState } from "react";
import { api, tokenStorage } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStorage.access) {
      setLoading(false);
      return;
    }
    api.get("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => tokenStorage.clear())
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const { data } = await api.post("/api/auth/login", { email, password });
    tokenStorage.set(data);
    const me = await api.get("/api/auth/me");
    setUser(me.data);
  }

  async function signup(email, password, fullName) {
    const { data } = await api.post("/api/auth/signup", {
      email,
      password,
      full_name: fullName || null,
    });
    tokenStorage.set(data);
    const me = await api.get("/api/auth/me");
    setUser(me.data);
  }

  function logout() {
    tokenStorage.clear();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
