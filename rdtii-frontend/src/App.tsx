import { Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/auth/Login";
import { RegisterPage } from "./pages/auth/Register";
import { AboutPage } from "./pages/menu/About";
import { LandingPage } from "./pages/menu/Landing";
import { WorkbenchPage } from "./pages/WorkbenchPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/workbench" element={<WorkbenchPage />} />
    </Routes>
  );
}
