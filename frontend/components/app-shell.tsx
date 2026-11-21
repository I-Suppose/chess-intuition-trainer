import { Link } from 'react-router-dom';
import { useLocation, useNavigate } from 'react-router-dom';
import { Activity, BookOpen, Brain, GitBranch, LayoutDashboard, LogOut, Settings, Swords } from 'lucide-react';
import { api } from '@/lib/api';
import { clearAccessToken } from '@/lib/auth';
import { ReactNode, useEffect, useState } from 'react';

const links = [{ href:'/dashboard',label:'Overview',icon:LayoutDashboard },{href:'/accounts',label:'Accounts',icon:Swords},{href:'/games',label:'Game library',icon:BookOpen},{href:'/openings',label:'Openings',icon:GitBranch},{href:'/puzzles',label:'Puzzle trainer',icon:Brain},{href:'/settings',label:'Settings',icon:Settings}];
export default function AppShell({ children, title }: { children:ReactNode; title:string }) {
  const path=useLocation().pathname, navigate=useNavigate(); const [email,setEmail]=useState('');
  useEffect(()=>{let active=true;api<{email:string}>('/auth/me').then(user=>{if(active)setEmail(user.email||'Player');}).catch(()=>{clearAccessToken();if(active)navigate('/');});return()=>{active=false};},[navigate]);
  function logout(){clearAccessToken();navigate('/');}
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">♞</div><span>Chess Intuition</span></div><nav className="nav">{links.map(({href,label,icon:Icon})=><Link className={path===href?'active':''} to={href} key={href}><Icon size={17}/>{label}</Link>)}</nav><div className="side-bottom"><Activity size={15}/> &nbsp;Your games. Your patterns.<br/><br/>Build intuition one decision at a time.</div></aside><div className="main"><header className="topbar"><div style={{fontSize:13,color:'#718078'}}>{title}</div><button className="button ghost" onClick={logout}><LogOut size={15}/> Sign out</button></header><main className="content"><div className="eyebrow">{email ? `Welcome back, ${email.split('@')[0]}` : 'Your training space'}</div>{children}</main></div></div>;
}
