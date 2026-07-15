import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { getRoleLandingPath } from "@/lib/roleRoutes";

export interface User {
  user_id: number;
  organization_id: number | null;
  username: string;
  role: string | null;
  full_name: string | null;
  email: string | null;
  active: boolean;
  created_at: string;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginFromGoogle: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "ovulite_token";
const REFRESH_TOKEN_KEY = "ovulite_refresh_token";
const TOKEN_REFRESH_INTERVAL = 25 * 60 * 1000; // 25 minutes (5 min before 30 min expiry)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_TOKEN_KEY));
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const loadUser = useCallback(async (accessToken: string) => {
    try {
      // Add 5 second timeout for loading user
      const loadUserPromise = api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error("User load timeout")), 5000)
      );
      
      const res = await Promise.race([loadUserPromise, timeoutPromise]) as Awaited<typeof loadUserPromise>;
      setUser(res.data);
    } catch (error) {
      console.error("[AuthContext] Failed to load user:", error);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      setToken(null);
      setRefreshToken(null);
      setUser(null);
    }
  }, []);

  const refreshAccessToken = useCallback(async () => {
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!storedRefreshToken) {
      console.log("[AuthContext] No refresh token available");
      return false;
    }

    try {
      console.log("[AuthContext] Refreshing access token...");
      const res = await api.post<{ access_token: string; refresh_token: string; token_type: string }>(
        "/auth/refresh",
        { refresh_token: storedRefreshToken },
      );

      const newAccessToken = res.data.access_token;
      localStorage.setItem(TOKEN_KEY, newAccessToken);
      setToken(newAccessToken);
      console.log("[AuthContext] Token refreshed successfully");
      return true;
    } catch (error) {
      console.error("[AuthContext] Token refresh failed:", error);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      setToken(null);
      setRefreshToken(null);
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    if (!token || !refreshToken) return;

    console.log("[AuthContext] Setting up automatic token refresh (every 25 min)");
    const interval = setInterval(() => {
      refreshAccessToken();
    }, TOKEN_REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [token, refreshToken, refreshAccessToken]);

  useEffect(() => {
    if (token) {
      loadUser(token).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onUnauthorized = async () => {
      console.log("[AuthContext] Received 401 - attempting token refresh");
      const refreshed = await refreshAccessToken();
      if (!refreshed) {
        navigate("/login");
      }
    };

    window.addEventListener("ovulite:unauthorized", onUnauthorized);
    return () => {
      window.removeEventListener("ovulite:unauthorized", onUnauthorized);
    };
  }, [navigate, refreshAccessToken]);

  const login = useCallback(
    async (username: string, password: string) => {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      console.log("[AuthContext] Attempting login for user:", username);
      try {
        const res = await api.post<{ access_token: string; refresh_token: string; token_type: string }>(
          "/auth/login",
          params,
          { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
        );

        console.log("[AuthContext] Login successful, got tokens");
        const accessToken = res.data.access_token;
        const refreshTokenValue = res.data.refresh_token;
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshTokenValue);
        setToken(accessToken);
        setRefreshToken(refreshTokenValue);

        console.log("[AuthContext] Fetching user profile with token...");
        const userRes = await api.get<User>("/auth/me", {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        console.log("[AuthContext] Got user profile:", userRes.data.username);
        setUser(userRes.data);

        navigate(getRoleLandingPath(userRes.data.role));
      } catch (error) {
        console.error("[AuthContext] Login failed:", error);
        throw error;
      }
    },
    [navigate],
  );

  const loginFromGoogle = useCallback(
    async (accessToken: string, refreshTokenValue: string) => {
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshTokenValue);
      setToken(accessToken);
      setRefreshToken(refreshTokenValue);

      const userRes = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      setUser(userRes.data);
      navigate(getRoleLandingPath(userRes.data.role));
    },
    [navigate],
  );



  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    navigate("/login");
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, loginFromGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
