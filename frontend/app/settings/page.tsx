'use client';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/app-shell';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
export default function Settings(){const router=useRouter();async function signOut(){await supabase()?.auth.signOut();router.replace('/');}return <AppShell title="Settings"><h1 className="page-title">Settings.</h1><p className="subtle">Manage your sign-in and connected chess profiles.</p><div className="card" style={{padding:22,marginTop:25}}><h3 style={{marginTop:0}}>Chess accounts</h3><p className="subtle">Refresh or disconnect public profiles and review import status.</p><Link href="/accounts" className="button" style={{textDecoration:'none'}}>Manage accounts</Link></div><div className="card" style={{padding:22,marginTop:15}}><h3 style={{marginTop:0}}>Sign-in</h3><p className="subtle">Authentication is managed securely by Supabase.</p><button className="button ghost" onClick={signOut}>Sign out</button></div></AppShell>}
