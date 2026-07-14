import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">
          <span className="brand-mark">T</span>
          TalkData
        </span>
        <nav>
          <NavLink to="/" end>Workspace</NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
        </nav>
        <span className="user-chip">
          {user.email}
          {user.role === "admin" && <span className="role-badge">admin</span>}
        </span>
        <button className="ghost" onClick={logout}>Log out</button>
      </header>
      <div className="main">
        <Outlet />
      </div>
    </div>
  );
}
