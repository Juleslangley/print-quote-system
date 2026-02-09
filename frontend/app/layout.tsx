import Nav from "./_components/Nav";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="app-body">
        <Nav />
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
