'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Activity, BookOpen, Brain, GitBranch, LayoutDashboard, LogOut, Settings, Swords } from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { ReactNode, useEffect, useState } from 'react';

const links = [{ href:'/dashboard',label:'Overview',icon:LayoutDashboard },{href:'/accounts',label:'Accounts',icon:Swords},{href:'/games',label:'Game library',icon:BookOpen},{href:'/openings',label:'Openings',icon:GitBranch},{href:'/puzzles',label:'Puzzle trainer',icon:Brain},{href:'/settings',label:'Settings',icon:Settings}];
export default function AppShell({ children, title }: { children:ReactNode; title:string }) {
  const path=usePathname(), router=useRouter(); const [email,setEmail]=useState('');
  useEffect(()=>{ const client=supabase(); if(!client){router.replace('/');return;} client.auth.getSession().then(({data})=>{if(!data.session)router.replace('/');else setEmail(data.session.user.email||'Player');}); },[router]);
  async function logout(){await supabase()?.auth.signOut();router.replace('/');}
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">♞</div><span>Chess Intuition</span></div><nav className="nav">{links.map(({href,label,icon:Icon})=><Link className={path===href?'active':''} href={href} key={href}><Icon size={17}/>{label}</Link>)}</nav><div className="side-bottom"><Activity size={15}/> &nbsp;Your games. Your patterns.<br/><br/>Build intuition one decision at a time.</div></aside><div className="main"><header className="topbar"><div style={{fontSize:13,color:'#718078'}}>{title}</div><button className="button ghost" onClick={logout}><LogOut size={15}/> Sign out</button></header><main className="content"><div className="eyebrow">{email ? `Welcome back, ${email.split('@')[0]}` : 'Your training space'}</div>{children}</main></div></div>;
}
