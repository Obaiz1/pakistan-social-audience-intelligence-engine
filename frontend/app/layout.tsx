import type { Metadata, Viewport } from "next";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/manrope/800.css";
import "@fontsource/ibm-plex-mono/400.css";
import "./globals.css";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: { default: "AudienceIQ PK", template: "%s · AudienceIQ PK" },
  description:
    "Pakistan Social Audience & Campaign Intelligence Engine (Clustering Based): content performance, multilingual comment clustering, unusual-post detection and evidence-linked recommendations.",
  icons: { icon: "/icon.svg" },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

// Applied before paint so a stored theme never flashes the wrong palette (Repo B pattern).
const themeScript = `try{var t=localStorage.getItem("audienceiq.theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <a href="#main" className="skip-link">Skip to content</a>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
