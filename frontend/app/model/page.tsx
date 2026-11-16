import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { ModelLabView } from "@/components/views/model";

export const metadata: Metadata = { title: "Model lab", description: "Pipeline, clustering experiments, audit metric definitions and method comparison." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <ModelLabView />
    </Suspense>
  );
}
