import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { RecommendationsView } from "@/components/views/recommendations";

export const metadata: Metadata = { title: "Recommendations", description: "Q5: evidence-linked recommendations with limitations and test plans." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <RecommendationsView />
    </Suspense>
  );
}
