import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { AudienceView } from "@/components/views/audience";

export const metadata: Metadata = { title: "Audience needs", description: "Q2/Q4: multilingual comment clusters, their profiles, language mix and campaign associations." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <AudienceView />
    </Suspense>
  );
}
