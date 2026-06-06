import Footer from "@/components/Footer/Footer";
import { Hero } from "@/components/Hero/Hero";
import { Label } from "@/components/Label/Label";
import { Description } from "@/components/Description/Description";
import { Placeholder } from "@/components/Placeholder";


export function LandingPage() {
  return (
    <main>
        <div className="relative">
            <Hero/>
            <Label/>
            <Description />
            <Placeholder />
            <Footer/>
        </div>
    </main>
  );
}