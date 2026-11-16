import Link from "next/link";

export default function NotFound() {
  return (
    <div className="empty">
      <h2>Page not found</h2>
      <p>This route does not exist in AudienceIQ PK.</p>
      <Link className="btn primary" href="/">Back to overview</Link>
    </div>
  );
}
