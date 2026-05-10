import { useNavigate } from "react-router-dom";
import { SignInPage } from "@/components/Signin/Signin";

const LoginPage = () => {
  const navigate = useNavigate();

  const handleSignIn = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate("/workbench");
  };

  return (
    <div className="bg-background text-foreground">
      <SignInPage
        heroImageSrc="https://images.unsplash.com/photo-1642615835477-d303d7dc9ee9?w=2160&q=80"
        onSignIn={handleSignIn}
        onGoogleSignIn={() => navigate("/workbench")}
        onResetPassword={() => navigate("/register")}
        onCreateAccount={() => navigate("/register")}
      />
    </div>
  );
};

export default LoginPage;
