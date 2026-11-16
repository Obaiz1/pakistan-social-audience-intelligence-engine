import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { CampaignsView } from "@/components/views/campaigns";

export const metadata: Metadata = { title: "Campaigns", description: "Q1/Q4: campaign comparison and audience needs by campaign." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <CampaignsView />
    </Suspense>
  );
}
