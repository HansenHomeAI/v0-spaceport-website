export const metadata = {
  title: 'Spaceport AI',
  description: 'Transform your drone footage into 3D models with Spaceport AI.',
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
    title: 'Spaceport AI',
    description: 'Transform your drone footage into 3D models with Spaceport AI.',
    url: 'https://spcprt.com',
    siteName: 'Spaceport AI',
    images: [
      {
        url: '/assets/SpaceportIcons/SpaceportSocialIcon.PNG',
        width: 1200,
        height: 630,
        alt: 'Spaceport AI Logo',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Spaceport AI',
    description: 'Transform your drone footage into 3D models with Spaceport AI.',
    images: ['/assets/SpaceportIcons/SpaceportSocialIcon.PNG'],
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

