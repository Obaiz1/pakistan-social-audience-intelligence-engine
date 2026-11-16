import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { ReportsView } from "@/components/views/reports";

export const metadata: Metadata = { title: "Reports & exports", description: "CSV, Excel and PDF exports with data-source disclosures." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <ReportsView />
    </Suspense>
  );
}
