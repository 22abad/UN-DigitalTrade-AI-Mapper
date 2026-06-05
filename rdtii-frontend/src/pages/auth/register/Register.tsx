import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { RegisterForm } from "@/components/Register/Register";
import { useAuth } from "@/hooks/useAuth";

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, isLoading } = useAuth();
  const [error, setError] = useState("");

  const handleRegister = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const username = (form.get("name") as string).trim();
    const email = (form.get("email") as string).trim();
    const password = form.get("password") as string;
    try {
      await register(username, email, password);
      navigate("/workbench", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  };

  return (
    <RegisterForm
      heroImageSrc="https://images.unsplash.com/photo-1642615835477-d303d7dc9ee9?w=2160&q=80"
      onRegister={handleRegister}
      onGoogleSignUp={() => navigate("/workbench")}
      onSignIn={() => navigate("/login")}
      error={error}
      isLoading={isLoading}
    />
  );
}
