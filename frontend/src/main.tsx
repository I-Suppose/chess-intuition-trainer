import React, { lazy, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@/components/theme-provider';
const SignIn = lazy(() => import('@/app/page'));
const Dashboard = lazy(() => import('@/app/dashboard/page'));
const Accounts = lazy(() => import('@/app/accounts/page'));
const Games = lazy(() => import('@/app/games/page'));
const GameAnalysis = lazy(() => import('@/app/games/[game_id]/analysis/page'));
const Openings = lazy(() => import('@/app/openings/page'));
const Puzzles = lazy(() => import('@/app/puzzles/page'));
const Puzzle = lazy(() => import('@/app/puzzles/[puzzle_id]/page'));
const PuzzleAnalysis = lazy(() => import('@/app/puzzles/[puzzle_id]/analysis/page'));
const Settings = lazy(() => import('@/app/settings/page'));
import '@/app/globals.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <Suspense fallback={<div className="card empty"><p className="subtle">Loading…</p></div>}>
        <Routes>
          <Route path="/" element={<SignIn />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/games" element={<Games />} />
          <Route path="/games/:game_id/analysis" element={<GameAnalysis />} />
          <Route path="/openings" element={<Openings />} />
          <Route path="/puzzles" element={<Puzzles />} />
          <Route path="/puzzles/:puzzle_id" element={<Puzzle />} />
          <Route path="/puzzles/:puzzle_id/analysis" element={<PuzzleAnalysis />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
);
