import ColorBends from "@/components/ColorBends/ColorBends";
import Footer from "@/components/Footer/Footer";
import { Hero } from "@/components/Hero/Hero";
import { Label } from "@/components/Label/Label";


export function LandingPage() {
  return (
    <main>
        <div className="relative">
            <Hero/>
            <Label/>
            {/* <Description /> */}
            <Footer/>
        </div>
    </main>
  );
}