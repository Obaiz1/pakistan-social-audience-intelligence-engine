import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { OverviewView } from "@/components/views/overview";

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <OverviewView />
    </Suspense>
  );
}
