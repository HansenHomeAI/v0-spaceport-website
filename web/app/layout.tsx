export const metadata = {
  title: 'Spaceport',
  description: 'Transform your drone footage into 3D models with Spaceport.',
  metadataBase: new URL('https://spcprt.com'),
  icons: {
    icon: [
      { url: '/assets/SpaceportIcons/Favicon.png' },
      { url: '/assets/SpaceportIcons/Favicon.png', type: 'image/png' },
    ],
    shortcut: '/assets/SpaceportIcons/Favicon.png',
    apple: '/assets/SpaceportIcons/Favicon.png',
  },
  openGraph: {
    title: 'Spaceport',
    description: 'Transform your drone footage into 3D models with Spaceport.',
    url: 'https://spcprt.com',
    siteName: 'Spaceport',
    images: [
      {
        url: '/assets/SpaceportIcons/SpcprtLarge.png',
        width: 1200,
        height: 630,
        alt: 'Spaceport Logo',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Spaceport',
    description: 'Transform your drone footage into 3D models with Spaceport.',
    images: ['/assets/SpaceportIcons/SpcprtLarge.png'],
  },
};
import './globals.css';
import '../public/styles.css';
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

