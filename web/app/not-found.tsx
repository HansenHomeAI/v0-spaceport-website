export const runtime = "edge";

export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <div>
        <h1 style={{ marginBottom: "0.75rem" }}>Page not found</h1>
        <p>The page you requested does not exist.</p>
      </div>
    </main>
  );
}
