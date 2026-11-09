import { useParams } from 'react-router-dom';
import GameAnalysisView from '@/components/game-analysis-view';
export default function PuzzleGameAnalysis(){const {puzzle_id=''}=useParams();return <GameAnalysisView params={{puzzle_id}} mode="puzzle"/>;}
