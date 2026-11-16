import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { ContentView } from "@/components/views/content";

export const metadata: Metadata = { title: "Content performance", description: "Q1: which content attracts attention — platform-aware engagement by content type, with uncertainty." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <ContentView />
    </Suspense>
  );
}
