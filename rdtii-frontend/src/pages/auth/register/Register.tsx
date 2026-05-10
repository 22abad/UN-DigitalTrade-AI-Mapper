import { useNavigate } from "react-router-dom";
import { RegisterForm } from "@/components/Register/Register";

export function RegisterPage() {
  const navigate = useNavigate();

  return (
    <RegisterForm
      heroImageSrc="https://images.unsplash.com/photo-1642615835477-d303d7dc9ee9?w=2160&q=80"
      onRegister={(e) => { e.preventDefault(); navigate("/workbench"); }}
      onGoogleSignUp={() => navigate("/workbench")}
      onSignIn={() => navigate("/login")}
    />
  );
}
