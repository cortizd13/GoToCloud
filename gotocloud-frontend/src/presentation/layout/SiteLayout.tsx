import type { ReactNode } from "react";
import { Header } from "./Header";
import { Footer } from "./Footer";

export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      <main id="top">{children}</main>
      <Footer />
    </>
  );
}
