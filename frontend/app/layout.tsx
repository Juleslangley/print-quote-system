import "./globals.css";
import Nav from "./_components/Nav";
import BackendHealthBanner from "./_components/BackendHealthBanner";
import DevDebugPanel from "./_components/DevDebugPanel";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="app-body">
        <BackendHealthBanner />
        <Nav />
        <DevDebugPanel />
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
