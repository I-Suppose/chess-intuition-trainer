import type { Metadata } from 'next';
import { ThemeProvider } from '@/components/theme-provider';
import './globals.css';
export const metadata: Metadata = { title: 'Chess Intuition Trainer', description: 'Train with positions from your own chess games.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><ThemeProvider>{children}</ThemeProvider></body></html>; }
