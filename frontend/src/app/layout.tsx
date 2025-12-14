import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { logger } from '@/utils/logger';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'CloneMemoria - AI Clones of Real People',
  description:
    'Create conversational AI clones of your loved ones with their memories and personality',
};

logger.info('Root layout loaded');

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

