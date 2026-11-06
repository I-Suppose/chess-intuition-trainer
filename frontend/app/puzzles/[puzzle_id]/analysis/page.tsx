'use client';
import { useParams } from 'next/navigation';
import GameAnalysisView from '@/components/game-analysis-view';
export default function PuzzleGameAnalysis(){const params=useParams<{puzzle_id:string}>();return <GameAnalysisView params={params} mode="puzzle"/>;}
