import { Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/login/Login";
import { RegisterPage } from "./pages/auth/register/Register";
import { AboutPage } from "./pages/menu/About";
import { TechMemoPage } from "./pages/menu/TechMemo";
import { LandingPage } from "./pages/menu/Landing";
import { WorkbenchPage } from "./pages/workbench/WorkbenchPage";
import { Navbar } from "./components/Navbar/Navbar";

export function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/workbench" element={<WorkbenchPage />} />
        <Route path="/tech_memo" element={<TechMemoPage />} />
      </Routes>
    </>
  );
}
