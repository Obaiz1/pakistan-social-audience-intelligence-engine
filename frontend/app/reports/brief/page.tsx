import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { BriefView } from "@/components/views/brief";

export const metadata: Metadata = { title: "Executive brief", description: "Printable executive brief grounded in the selected dataset." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <BriefView />
    </Suspense>
  );
}
