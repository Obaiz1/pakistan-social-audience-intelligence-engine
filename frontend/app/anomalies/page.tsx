import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { AnomaliesView } from "@/components/views/anomalies";

export const metadata: Metadata = { title: "Unusual patterns", description: "Q3: posts that differ substantially from comparable posts, with baselines and reasons." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <AnomaliesView />
    </Suspense>
  );
}
