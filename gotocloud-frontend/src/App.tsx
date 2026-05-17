import { SiteLayout } from "./presentation/layout/SiteLayout";
import { ContactSection } from "./presentation/sections/ContactSection";
import { DashboardSection } from "./presentation/sections/DashboardSection";
import ContactCenterButton from "./presentation/layout/ContactCenterButton";

export default function App() {
  const isDashboard = window.location.pathname.startsWith("/dashboard");

  if (isDashboard) {
    return <DashboardSection />;
  }

  return (
    <>
      <SiteLayout>
        <ContactSection />
      </SiteLayout>
      <ContactCenterButton />
    </>
  );
}
