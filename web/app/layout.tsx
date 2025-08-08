export const metadata = { title: 'Spaceport AI' };
import './globals.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/assets/SpaceportIcons/SpaceportSocialIcon.PNG" />
      </head>
      <body>{children}</body>
    </html>
  );
}
