import { GoogleLogin } from '@react-oauth/google';
import { useState } from 'react';
import api from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

interface GoogleAuthButtonProps {
  isDark: boolean;
  onLoading?: (isLoading: boolean) => void;
  onError?: (error: string) => void;
}

export const GoogleAuthButton = ({ isDark, onLoading, onError }: GoogleAuthButtonProps) => {
  const { loginFromGoogle } = useAuth();
  const navigate = useNavigate();
  const [processing, setProcessing] = useState(false);

  const isPlaceholder = !import.meta.env.VITE_GOOGLE_CLIENT_ID || 
                        import.meta.env.VITE_GOOGLE_CLIENT_ID.includes("your-google-client-id");

  const handleMockLogin = async () => {
    setProcessing(true);
    onLoading?.(true);
    try {
      console.log("[GoogleAuth] Starting mock login flow...");
      const res = await api.post("/auth/google/mock");
      await loginFromGoogle(res.data.access_token, res.data.refresh_token);
      navigate("/dashboard");
    } catch {
      onError?.("Demo login failed. Make sure to RESTART your backend.");
    } finally {
      setProcessing(false);
      onLoading?.(false);
    }
  };

  const handleSuccess = async (credentialResponse: any) => {
    setProcessing(true);
    onLoading?.(true);
    try {
      console.log("[GoogleAuth] Received JWT (ID Token), sending to backend...");
      const res = await api.post("/auth/google", {
        token: credentialResponse.credential, // This is the JWT
      });

      await loginFromGoogle(res.data.access_token, res.data.refresh_token);
      navigate("/dashboard");
    } catch (err: any) {
      console.error("[GoogleAuth] Auth failed:", err);
      onError?.(err.response?.data?.detail || "Authentication failed");
    } finally {
      setProcessing(false);
      onLoading?.(false);
    }
  };

  if (isPlaceholder) {
    return (
      <button
        type="button"
        onClick={handleMockLogin}
        disabled={processing}
        className="flex w-full items-center justify-center gap-3 rounded-full py-4 text-sm font-bold shadow-sm transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70"
        style={{
          background: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.75)",
          border: isDark ? "1px solid rgba(255,255,255,0.08)" : "1px solid #e2e8f0",
          color: isDark ? "#e4e4e7" : "#1e293b",
          fontSize: "15px",
          fontFamily: '"Inter", sans-serif',
          fontWeight: 600,
        }}
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
        </svg>
        {processing ? "Processing..." : "Continue with Google (Demo)"}
      </button>
    );
  }

  return (
    <div className="flex w-full justify-center">
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={() => onError?.("Google login failed")}
        theme={isDark ? "filled_black" : "outline"}
        shape="pill"
        width="340"
        text="continue_with"
      />
    </div>
  );
};
