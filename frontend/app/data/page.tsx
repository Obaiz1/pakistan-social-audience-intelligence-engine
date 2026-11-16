import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { DataView } from "@/components/views/data";

export const metadata: Metadata = { title: "Data & imports", description: "Datasets, provenance, quality audit, demo generator and CSV import." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <DataView />
    </Suspense>
  );
}
