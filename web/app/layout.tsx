export const metadata = {
  title: 'Spaceport AI',
  icons: {
    icon: [
      { url: '/assets/SpaceportIcons/Favicon.png' },
      { url: '/assets/SpaceportIcons/Favicon.png', type: 'image/png' },
    ],
    shortcut: '/assets/SpaceportIcons/Favicon.png',
    apple: '/assets/SpaceportIcons/Favicon.png',
  },
};
import './globals.css';
import 'mapbox-gl/dist/mapbox-gl.css';
import Header from '../components/Header';
import Footer from '../components/Footer';
import AnalyticsProvider from '../components/AnalyticsProvider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/assets/SpaceportIcons/Favicon.png" />
        <link rel="apple-touch-icon" href="/assets/SpaceportIcons/Favicon.png" />
        <meta name="theme-color" content="#000000" />
      </head>
      <body>
        <AnalyticsProvider>
          <Header />
          {children}
          <Footer />
        </AnalyticsProvider>
      </body>
    </html>
  );
}
