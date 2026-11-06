'use client';
import { useParams } from 'next/navigation';
import GameAnalysisView from '@/components/game-analysis-view';
export default function GameAnalysis(){const params=useParams<{game_id:string}>();return <GameAnalysisView params={{puzzle_id:params.game_id}} mode="game"/>;}
