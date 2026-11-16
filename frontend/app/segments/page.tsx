import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { SegmentsView } from "@/components/views/segments";

export const metadata: Metadata = { title: "Segments", description: "Q4: comment-level need segments with share, examples, campaign lift and comparisons." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <SegmentsView />
    </Suspense>
  );
}
