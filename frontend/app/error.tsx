"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <div className="empty" role="alert">
      <h2>This view failed to render</h2>
      <p>Something went wrong while drawing this page. No data was changed.</p>
      <button className="btn primary" type="button" onClick={() => reset()}>Try again</button>
    </div>
  );
}
