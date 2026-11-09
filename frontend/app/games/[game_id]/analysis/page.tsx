import { useParams } from 'react-router-dom';
import GameAnalysisView from '@/components/game-analysis-view';
export default function GameAnalysis(){const {game_id=''}=useParams();return <GameAnalysisView params={{puzzle_id:game_id}} mode="game"/>;}
