import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Chess Intuition Trainer', description: 'Train with positions from your own chess games.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
