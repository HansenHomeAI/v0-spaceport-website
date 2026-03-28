export const runtime = "edge";

export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
        background: "#0b1020",
        color: "#f8fafc",
        fontFamily: "system-ui, sans-serif",
        textAlign: "center",
      }}
    >
      <div>
        <h1 style={{ margin: 0, fontSize: "2rem" }}>Page not found</h1>
        <p style={{ marginTop: "0.75rem", opacity: 0.8 }}>
          The requested page does not exist in this preview.
        </p>
      </div>
    </main>
  );
}
