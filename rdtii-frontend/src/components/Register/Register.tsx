import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

const GoogleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 48 48">
    <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s12-5.373 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-2.641-.21-5.236-.611-7.743z" />
    <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" />
    <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" />
    <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.022 35.026 44 30.038 44 24c0-2.641-.21-5.236-.611-7.743z" />
  </svg>
);

const GlassInputWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-2xl border border-border bg-foreground/5 backdrop-blur-sm transition-colors focus-within:border-[#10B981]/70 focus-within:bg-[#10B981]/10">
    {children}
  </div>
);

interface RegisterFormProps {
  heroImageSrc?: string;
  onRegister?: (event: React.FormEvent<HTMLFormElement>) => void;
  onGoogleSignUp?: () => void;
  onSignIn?: () => void;
  error?: string;
  isLoading?: boolean;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({
  heroImageSrc,
  onRegister,
  onGoogleSignUp,
  onSignIn,
  error,
  isLoading,
}) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="h-[100dvh] flex flex-col md:flex-row font-geist w-[100dvw] bg-background text-foreground">

      {/* Left: form */}
      <section className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex flex-col gap-6">

            <h1 className="text-4xl md:text-5xl font-light leading-tight">
              Join <a href="/" className="text-[#10B981] bg-gradient-to-r from-[#10B981] to-[#10B981] bg-[length:0%_1.5px] hover:bg-[length:100%_1.5px] bg-left-bottom bg-no-repeat transition-all duration-500 cursor-pointer">Sentinel</a>
            </h1>
            <p className="text-muted-foreground">
              Create your account to access the digital trade evidence workbench.
            </p>

            <form className="space-y-5" onSubmit={onRegister}>
              <div className="mt-10">
                <label className="text-sm font-medium text-muted-foreground mb-2">Full Name</label>
                <GlassInputWrapper>
                  <input name="name" type="text" placeholder="Enter your full name" className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none" />
                </GlassInputWrapper>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2">Email Address</label>
                <GlassInputWrapper>
                  <input name="email" type="email" placeholder="Enter your email address" className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none" />
                </GlassInputWrapper>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2">Password</label>
                <GlassInputWrapper>
                  <div className="relative">
                    <input name="password" type={showPassword ? "text" : "password"} placeholder="Create a password" className="w-full bg-transparent text-sm p-4 pr-12 rounded-2xl focus:outline-none" />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-3 flex items-center bg-transparent">
                      {showPassword
                        ? <EyeOff className="w-5 h-5 text-black transition-colors" />
                        : <Eye className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />}
                    </button>
                  </div>
                </GlassInputWrapper>
              </div>

              {error && <p className="text-sm text-red-500 text-center">{error}</p>}
              <button type="submit" disabled={isLoading} className="w-full rounded-2xl bg-[#10B981] py-4 font-medium text-white hover:bg-[#0da373] disabled:opacity-50 transition-colors">
                {isLoading ? "Creating account…" : "Create Account"}
              </button>
            </form>

            <div className="relative flex items-center justify-center">
              <span className="w-full border-t border-border"></span>
              <span className="mt-10 px-5 text-sm text-muted-foreground bg-background absolute">Or continue with</span>
            </div>

            <button onClick={onGoogleSignUp} className="animate-element animate-delay-800 w-full flex items-center justify-center gap-3 border border-border rounded-2xl py-4 hover:border-[#10B981] hover:text-[#10B981] hover:bg-[#10B981]/5 transition-colors mt-5">
                <GoogleIcon />
                Continue with Google
            </button>

            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); onSignIn?.(); }} className="text-[#10B981] hover:underline transition-colors">Sign In</a>
            </p>

          </div>
        </div>
      </section>

      {/* Right: hero image */}
      {heroImageSrc && (
        <section className="hidden md:block flex-1 relative p-4">
          <div className="absolute inset-4 rounded-3xl bg-cover bg-center" style={{ backgroundImage: `url(${heroImageSrc})` }} />
        </section>
      )}

    </div>
  );
};
