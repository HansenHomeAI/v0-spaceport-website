export const runtime = "edge";

export default function NotFound() {
  return (
    <main style={{ padding: "3rem 1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Page not found</h1>
      <p>The requested page does not exist.</p>
    </main>
  );
}
