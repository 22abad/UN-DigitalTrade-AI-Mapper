import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SignInPage } from "@/components/Signin/Signin";
import { useAuth } from "@/hooks/useAuth";

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, isLoading } = useAuth();
  const [error, setError] = useState("");

  const handleSignIn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const email = (form.get("email") as string).trim();
    const password = form.get("password") as string;
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="bg-background text-foreground">
      <SignInPage
        heroImageSrc="https://images.unsplash.com/photo-1642615835477-d303d7dc9ee9?w=2160&q=80"
        onSignIn={handleSignIn}
        onGoogleSignIn={() => navigate("/")}
        onResetPassword={() => navigate("/register")}
        onCreateAccount={() => navigate("/register")}
        error={error}
        isLoading={isLoading}
      />
    </div>
  );
};

export default LoginPage;
