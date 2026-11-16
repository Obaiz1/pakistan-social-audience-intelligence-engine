import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingPage } from "@/components/ui";
import { CommentsView } from "@/components/views/comments";

export const metadata: Metadata = { title: "Comment explorer", description: "Q2: privacy-aware comment explorer with language, reference topic, intent and cluster." };

export default function Page() {
  return (
    <Suspense fallback={<LoadingPage />}>
      <CommentsView />
    </Suspense>
  );
}
