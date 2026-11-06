export type GameOutcome='win'|'loss'|'draw';

const drawResults=new Set(['draw','stalemate','agreed','repetition','insufficient','50move','fiftymove','timevsinsufficient','threecheck','1/2-1/2']);
const lossResults=new Set(['loss','lost','checkmated','resigned','timeout','abandoned','lose']);

export function gameOutcome(result:string|null|undefined,userColour?:string|null):GameOutcome{
  const value=(result||'').trim().toLowerCase().replace(/\s+/g,'');
  if(value==='win'||value==='won')return 'win';
  if(lossResults.has(value))return 'loss';
  if(drawResults.has(value))return 'draw';
  if(value==='1-0')return userColour==='white'?'win':'loss';
  if(value==='0-1')return userColour==='black'?'win':'loss';
  // Chess.com exposes a terminal reason for the user's side; non-winning terminal
  // reasons not classified as a loss are draw endings (including older imports).
  return 'draw';
}
