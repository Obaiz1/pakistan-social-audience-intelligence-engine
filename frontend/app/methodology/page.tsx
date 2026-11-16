import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { MethodologyView } from "@/components/views/methodology";

export const metadata: Metadata = { title: "Methodology", description: "Project 3 methodology: questions, formulas, models, evaluation, limitations and reproducibility." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <MethodologyView />
    </Suspense>
  );
}
