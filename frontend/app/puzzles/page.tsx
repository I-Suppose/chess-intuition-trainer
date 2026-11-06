'use client';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Brain, Check, CheckCircle2 } from 'lucide-react';
import AppShell from '@/components/app-shell';
import { api } from '@/lib/api';

const categories=['All puzzles','Brilliant Move','Missed Brilliant Opportunity','Tactical Combination','Winning Move','Defensive Resource','Critical Decision','Great Move','Tactical Mistake'];
type Puzzle={id:string;game_id:string;white_player:string|null;black_player:string|null;result:string|null;category:string;priority:number;side_to_move:string;game_move_number:number;opening_name:string|null;opening_line:string|null;opponent_username:string|null;played_at:string|null;platform:string;game_url:string|null;completed:boolean;solved:boolean;revealed:boolean};
type Progress={games_imported:number;puzzles_generated:number;analysis_pending:number;analysis_failed:number;analysis_complete:number};
type History={items:{puzzle_id:string;attempted_at:string;is_correct:boolean;revealed?:boolean;category:string;opening_name:string|null;game_move_number:number}[];total:number};
type OpeningGroup={name:string;puzzles:Puzzle[]};

function openingFamily(name:string|null){
  const value=(name||'').replace(/[’‘]/g,"'").replace(/\s+/g,' ').trim();
  if(!value)return 'Opening not classified';
  const families:[RegExp,string][]=[
    [/queen'?s gambit/i,"Queen's Gambit"],[/queen'?s pawn/i,"Queen's Pawn Openings"],
    [/king'?s indian/i,"King's Indian Defense"],[/king'?s gambit/i,"King's Gambit"],
    [/queen'?s indian/i,"Queen's Indian Defense"],[/nimzo[- ]indian/i,'Nimzo-Indian Defense'],
    [/caro[- ]?kann/i,'Caro-Kann Defense'],[/sicilian/i,'Sicilian Defense'],[/french/i,'French Defense'],
    [/ruy lopez/i,'Ruy Lopez'],[/spanish opening/i,'Ruy Lopez'],[/italian game/i,'Italian Game'],
    [/english opening/i,'English Opening'],[/reti|réti/i,'Réti Opening'],[/gr[uü]nfeld/i,'Grünfeld Defense'],
    [/slav/i,'Slav Defense'],[/scandinavian/i,'Scandinavian Defense'],[/dutch/i,'Dutch Defense'],
    [/pirc/i,'Pirc Defense'],[/ale[ck]hine/i,'Alekhine Defense'],[/king'?s pawn/i,"King's Pawn Openings"],
    [/vienna/i,'Vienna Game'],[/petrov|russian game/i,'Petrov Defense'],[/modern defense/i,'Modern Defense'],
    [/reti|réti/i,'Réti Opening']
  ];
  return families.find(([pattern])=>pattern.test(value))?.[1]||value.split(/\s+(?:Defense|Opening|Game|Variation|Attack|System|Line)\b/i)[0].trim()||value;
}

function openingGroups(items:Puzzle[]):OpeningGroup[]{
  const groups=new Map<string,Puzzle[]>();
  for(const puzzle of items){const name=openingFamily(puzzle.opening_name);groups.set(name,[...(groups.get(name)||[]),puzzle]);}
  return Array.from(groups,([name,puzzles])=>({name,puzzles:puzzles.sort((a,b)=>(a.played_at||'').localeCompare(b.played_at||'')||a.game_move_number-b.game_move_number)}))
    .sort((a,b)=>b.puzzles.length-a.puzzles.length||a.name.localeCompare(b.name));
}

export default function Puzzles(){
  const [category,setCategory]=useState('All puzzles'),[items,setItems]=useState<Puzzle[]>([]),[progress,setProgress]=useState<Progress>(),[history,setHistory]=useState<History>(),[loading,setLoading]=useState(true),[error,setError]=useState('');
  useEffect(()=>{let active=true;setLoading(true);setError('');(async()=>{try{const params=new URLSearchParams({page:'1',page_size:'100'});if(category!=='All puzzles')params.set('category',category);const first=await api<{items:Puzzle[];total:number}>(`/puzzles?${params}`);const all=[...first.items];for(let page=2;all.length<first.total;page++){const nextParams=new URLSearchParams(params);nextParams.set('page',String(page));const next=await api<{items:Puzzle[];total:number}>(`/puzzles?${nextParams}`);if(!next.items.length)break;all.push(...next.items);}if(active)setItems(all);}catch(e){if(active)setError(e instanceof Error?e.message:'Could not load your puzzles.');}finally{if(active)setLoading(false);}})();api<Progress>('/progress').then(value=>{if(active)setProgress(value)}).catch(()=>{});api<History>('/progress/history?page=1&page_size=5').then(value=>{if(active)setHistory(value)}).catch(()=>{});return()=>{active=false};},[category]);
  const active=useMemo(()=>items.filter(item=>!item.completed),[items]),completed=useMemo(()=>items.filter(item=>item.completed),[items]);
  const activeGroups=useMemo(()=>openingGroups(active),[active]),completedGroups=useMemo(()=>openingGroups(completed),[completed]);
  function tileSections(groups:OpeningGroup[],isComplete:boolean){return <div className="opening-tile-sections">{groups.map(group=><section className="opening-tile-section card" key={`${isComplete}-${group.name}`}><div className="opening-tile-heading"><div><h3>{group.name}</h3><p>{group.puzzles.length} {group.puzzles.length===1?'puzzle':'puzzles'}</p></div><span className="opening-tile-badge">{isComplete?<CheckCircle2 size={18}/>:group.puzzles.length}</span></div><div className="opening-tiles">{group.puzzles.map((puzzle,index)=><Link className={`opening-tile ${isComplete?'completed':''}`} href={`/puzzles/${puzzle.id}`} key={puzzle.id} title={`${group.name} · ${puzzle.category} · move ${puzzle.game_move_number}`} aria-label={`${group.name}, move ${puzzle.game_move_number}, ${isComplete?'completed':'solve puzzle'}`}><span className="opening-tile-number">{isComplete?<Check size={26} strokeWidth={3}/>:index+1}</span><span className="opening-tile-move">Move {puzzle.game_move_number}</span></Link>)}</div></section>)}</div>;}
  return <AppShell title="Puzzle trainer"><div className="puzzle-page-heading"><div><div className="eyebrow">Your game-based training</div><h1 className="page-title">Solve puzzles from your games.</h1><p className="subtle">Each tile is a turning point from your games, grouped with similar openings.</p></div><label className="puzzle-filter"><span>Filter</span><select className="filter-select" aria-label="Filter puzzle category" value={category} onChange={event=>setCategory(event.target.value)}>{categories.map(item=><option key={item} value={item}>{item}</option>)}</select></label></div>
    {error&&<div className="alert">{error}</div>}{loading?<div className="card empty"><p className="subtle">Loading your game positions…</p></div>:<><section className="puzzle-section"><div className="section-head puzzle-section-head"><h2>Puzzle trainer <span className="subtle">{active.length}</span></h2></div>{active.length?tileSections(activeGroups,false):<div className="card empty puzzle-empty"><Brain size={25} color="#78917d"/><h3>{progress?.games_imported===0?'Connect an account to get started':progress?.analysis_pending?'Analyzing your game decisions':progress?.analysis_failed?'Some games need analysis retry':'No puzzles waiting'}</h3><p className="subtle">{progress?.games_imported===0?'Import your Chess.com or Lichess games to create a personal puzzle library.':progress?.analysis_pending?`${progress.analysis_pending} games are queued or being analyzed. Puzzles will appear as important positions are found.`:progress?.analysis_failed?`${progress.analysis_failed} games could not be analyzed. You can retry analysis from the game library.`:'You have finished all puzzles in this filter.'}</p>{progress?.games_imported===0&&<Link href="/accounts" className="button" style={{textDecoration:'none',marginTop:16}}>Connect accounts</Link>}</div>}</section><section className="puzzle-section"><div className="section-head puzzle-section-head"><h2>Complete <span className="subtle">{completed.length}</span></h2></div>{completed.length?tileSections(completedGroups,true):<div className="card puzzle-complete-empty subtle">Completed puzzles will be kept here, separate from the trainer.</div>}</section></>}
    {history?.items?.length?<><div className="section-head"><h2>Recent attempts</h2></div><div className="card" style={{padding:'4px 18px'}}>{history.items.map((item,index)=><Link key={`${item.puzzle_id}-${item.attempted_at}-${index}`} href={`/puzzles/${item.puzzle_id}`} className="line-row" style={{textDecoration:'none',color:'inherit'}}><span>{item.category} · {item.opening_name||'Game position'} · move {item.game_move_number}</span><span className={`pill ${item.revealed?'pending':item.is_correct?'':'failed'}`}>{item.revealed?'Solution viewed':item.is_correct?'Correct':'Try again'}</span></Link>)}</div></>:null}</AppShell>;
}
