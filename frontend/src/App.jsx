import { useState } from 'react'
import { Routes, Route, NavLink, useNavigate, Navigate } from 'react-router-dom'
import { Scale, FileText, MessageSquare, ArrowRight, Zap, Globe, Shield, Sparkles, Check, Coins, LogOut, User, Sun, Moon } from 'lucide-react'
import { useAuth } from './context/AuthContext'
import { useTheme } from './context/ThemeContext'
import ChatPage from './pages/ChatPage'
import DocBuilderPage from './pages/DocBuilderPage'
import AuthPage from './pages/AuthPage'
import TokenModal from './components/TokenModal'

// CSS variable-based tokens — always current theme
export const T = {
  get bg()          { return 'var(--bg)' },
  get surface()     { return 'var(--surface)' },
  get raised()      { return 'var(--raised)' },
  get border()      { return 'var(--border)' },
  get borderDark()  { return 'var(--borderDark)' },
  get text()        { return 'var(--text)' },
  get sub()         { return 'var(--sub)' },
  get dim()         { return 'var(--dim)' },
  get muted()       { return 'var(--muted)' },
  get blue()        { return 'var(--blue)' },
  get blueDark()    { return 'var(--blueDark)' },
  get blueLight()   { return 'var(--blueLight)' },
  get blueMid()     { return 'var(--blueMid)' },
  get amber()       { return 'var(--amber)' },
  get amberDark()   { return 'var(--amberDark)' },
  get amberLight()  { return 'var(--amberLight)' },
  get green()       { return 'var(--green)' },
  get greenLight()  { return 'var(--greenLight)' },
}

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div style={{ height:'100%', display:'flex', alignItems:'center', justifyContent:'center' }}>
      <div style={{ width:24, height:24, border:`2px solid var(--border)`, borderTopColor:'var(--blue)', borderRadius:'50%' }} className="spin"/>
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  return children
}

function TokenBadge({ onBuy }) {
  const { user } = useAuth()
  const isLow = (user?.tokens || 0) < 10
  return (
    <button onClick={onBuy} style={{ display:'flex', alignItems:'center', gap:6, padding:'5px 12px', borderRadius:9999, background: isLow ? 'rgba(239,68,68,0.1)' : 'var(--blueLight)', border:`1px solid ${isLow ? 'rgba(239,68,68,0.3)' : 'rgba(var(--blue-rgb,59,91,219),0.25)'}`, cursor:'pointer', fontSize:13, fontWeight:600, color: isLow ? '#EF4444' : 'var(--blue)', transition:'all .15s' }}>
      <Coins size={13}/>{user?.tokens ?? '—'} tokens
    </button>
  )
}

function ThemeToggle() {
  const { isDark, toggle } = useTheme()
  return (
    <button onClick={toggle} title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{ width:34, height:34, borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', background:'var(--muted)', border:'1px solid var(--border)', cursor:'pointer', color:'var(--sub)', transition:'all .15s' }}
      onMouseEnter={e=>{ e.currentTarget.style.color='var(--text)'; e.currentTarget.style.borderColor='var(--borderDark)' }}
      onMouseLeave={e=>{ e.currentTarget.style.color='var(--sub)'; e.currentTarget.style.borderColor='var(--border)' }}>
      {isDark ? <Sun size={15}/> : <Moon size={15}/>}
    </button>
  )
}

export function Nav() {
  const { user, signOut } = useAuth()
  const [showTokens, setShowTokens] = useState(false)
  const navigate = useNavigate()

  return (
    <>
      <header style={{ background:'var(--surface)', borderBottom:'1px solid var(--border)', height:56, display:'flex', alignItems:'center', padding:'0 24px', justifyContent:'space-between', position:'sticky', top:0, zIndex:50, transition:'background .2s' }}>
        <NavLink to="/" style={{ display:'flex', alignItems:'center', gap:10, textDecoration:'none' }}>
          <div style={{ width:34, height:34, borderRadius:10, background:'linear-gradient(135deg, var(--blue), var(--blueMid))', display:'flex', alignItems:'center', justifyContent:'center' }}>
            <Scale size={17} color="white" strokeWidth={2.2}/>
          </div>
          <span style={{ fontFamily:'"Plus Jakarta Sans"', fontWeight:800, fontSize:16, color:'var(--text)', letterSpacing:'-0.02em' }}>
            Nyaya<span style={{ color:'var(--blue)' }}>Flow</span>
          </span>
        </NavLink>

        <div style={{ display:'flex', gap:4 }}>
          {[{to:'/chat',label:'Legal Chat',icon:MessageSquare},{to:'/docs',label:'Draft Document',icon:FileText}].map(({to,label,icon:Icon})=>(
            <NavLink key={to} to={to}
              style={({isActive})=>({ display:'flex', alignItems:'center', gap:6, padding:'6px 14px', borderRadius:8, fontSize:13, fontFamily:'"Plus Jakarta Sans"', fontWeight:600, textDecoration:'none', transition:'all .15s', background: isActive ? 'var(--blueLight)' : 'transparent', color: isActive ? 'var(--blue)' : 'var(--sub)', border:`1px solid ${isActive ? 'rgba(59,91,219,0.25)' : 'transparent'}` })}>
              <Icon size={13}/>{label}
            </NavLink>
          ))}
        </div>

        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <TokenBadge onBuy={()=>setShowTokens(true)}/>
          <div style={{ display:'flex', alignItems:'center', gap:8, padding:'5px 12px', background:'var(--muted)', borderRadius:9999, border:'1px solid var(--border)' }}>
            <div style={{ width:24, height:24, borderRadius:'50%', background:'linear-gradient(135deg,var(--blue),var(--blueMid))', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <User size={12} color="white"/>
            </div>
            <span style={{ fontSize:13, fontWeight:500, color:'var(--text)' }}>{user?.name?.split(' ')[0]}</span>
          </div>
          <ThemeToggle/>
          <button onClick={()=>{signOut();navigate('/')}} title="Sign out"
            style={{ background:'none', border:'none', cursor:'pointer', color:'var(--dim)', padding:6, borderRadius:8, transition:'all .15s', display:'flex', alignItems:'center' }}
            onMouseEnter={e=>{ e.currentTarget.style.background='var(--muted)'; e.currentTarget.style.color='var(--text)' }}
            onMouseLeave={e=>{ e.currentTarget.style.background='none'; e.currentTarget.style.color='var(--dim)' }}>
            <LogOut size={16}/>
          </button>
        </div>
      </header>
      {showTokens && <TokenModal onClose={()=>setShowTokens(false)}/>}
    </>
  )
}

function Landing() {
  const nav = useNavigate()
  const { user } = useAuth()
  const { isDark, toggle } = useTheme()

  const features = [
    { icon:Zap,      title:'Instant legal answers',  desc:'Ask in plain English or Hindi. Answers cite specific Act sections — no generic advice.' },
    { icon:Globe,    title:'Self-learning corpus',   desc:'Unknown laws fetched from indiacode.nic.in automatically and saved permanently.' },
    { icon:FileText, title:'AI document drafting',   desc:'Rental agreements, NDAs, affidavits and offer letters as downloadable PDFs.' },
    { icon:Shield,   title:'Always cited',           desc:'Every answer references the exact Act, section and page — zero hallucination.' },
  ]

  const useCases = ['Consumer Rights','Property Law','RTI Act','IT Act','Contract Law','Company Law','Motor Vehicles','Criminal Law','Labour Law','Family Law']

  return (
    <div style={{ fontFamily:'"Plus Jakarta Sans"', background:'var(--bg)', minHeight:'100vh', transition:'background .2s' }}>
      <header style={{ background:'var(--surface)', borderBottom:'1px solid var(--border)', height:60, display:'flex', alignItems:'center', padding:'0 48px', justifyContent:'space-between', transition:'background .2s' }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <div style={{ width:36,height:36,borderRadius:10,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'flex',alignItems:'center',justifyContent:'center' }}>
            <Scale size={18} color="white" strokeWidth={2.2}/>
          </div>
          <span style={{ fontWeight:800,fontSize:17,color:'var(--text)',letterSpacing:'-0.02em' }}>Nyaya<span style={{ color:'var(--blue)' }}>Flow</span></span>
        </div>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          <button onClick={toggle} style={{ width:34,height:34,borderRadius:9,display:'flex',alignItems:'center',justifyContent:'center',background:'var(--muted)',border:'1px solid var(--border)',cursor:'pointer',color:'var(--sub)' }}>
            {isDark?<Sun size={15}/>:<Moon size={15}/>}
          </button>
          {user ? (
            <button onClick={()=>nav('/chat')} style={{ padding:'8px 20px',borderRadius:8,background:'var(--blue)',color:'white',border:'none',fontSize:13,fontWeight:700,cursor:'pointer' }}>Go to App</button>
          ) : (
            <>
              <button onClick={()=>nav('/login')} style={{ padding:'8px 20px',borderRadius:8,background:'transparent',color:'var(--sub)',border:'1px solid var(--border)',fontSize:13,fontWeight:600,cursor:'pointer' }}>Login</button>
              <button onClick={()=>nav('/register')} style={{ padding:'8px 20px',borderRadius:8,background:'var(--blue)',color:'white',border:'none',fontSize:13,fontWeight:700,cursor:'pointer' }}>Get Started Free</button>
            </>
          )}
        </div>
      </header>

      <section style={{ maxWidth:1100,margin:'0 auto',padding:'80px 48px 60px',display:'grid',gridTemplateColumns:'1fr 1fr',gap:60,alignItems:'center' }}>
        <div className="fade-up">
          <div style={{ display:'inline-flex',alignItems:'center',gap:7,background:'var(--amberLight)',border:'1px solid rgba(245,158,11,0.3)',borderRadius:9999,padding:'5px 14px',marginBottom:24,fontSize:12,color:'var(--amberDark)',fontWeight:700 }}>
            <Sparkles size={12}/>India's Legal AI — Powered by RAG
          </div>
          <h1 style={{ fontFamily:'"Fraunces"',fontWeight:700,fontSize:52,lineHeight:1.08,letterSpacing:'-0.03em',color:'var(--text)',marginBottom:20 }}>
            Legal answers<br/><span style={{ fontStyle:'italic',color:'var(--blue)' }}>for every Indian.</span>
          </h1>
          <p style={{ fontSize:17,color:'var(--sub)',lineHeight:1.7,marginBottom:36,maxWidth:440 }}>
            Ask about consumer rights, property disputes, or any Indian law. Get precise answers with section citations — in seconds.
          </p>
          <div style={{ display:'flex',gap:12,flexWrap:'wrap',marginBottom:40 }}>
            <button onClick={()=>nav(user?'/chat':'/register')} style={{ display:'inline-flex',alignItems:'center',gap:8,background:'var(--blue)',color:'white',border:'none',borderRadius:10,padding:'13px 24px',fontSize:15,fontWeight:700,cursor:'pointer' }}>
              {user?'Go to App':'Start Free — 100 tokens'}<ArrowRight size={16}/>
            </button>
            <button onClick={()=>nav('/docs')} style={{ display:'inline-flex',alignItems:'center',gap:8,background:'var(--surface)',color:'var(--text)',border:'1px solid var(--borderDark)',borderRadius:10,padding:'13px 24px',fontSize:15,fontWeight:600,cursor:'pointer' }}>
              <FileText size={15}/>Draft a Document
            </button>
          </div>
          <div style={{ display:'flex',gap:20,flexWrap:'wrap' }}>
            {['100 free tokens on signup','No credit card needed','Powered by Indian legal corpus'].map(t=>(
              <div key={t} style={{ display:'flex',alignItems:'center',gap:6,fontSize:13,color:'var(--dim)' }}>
                <Check size={13} color="var(--green)"/>{t}
              </div>
            ))}
          </div>
        </div>

        <div className="fade-up" style={{ animationDelay:'.15s' }}>
          <div style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:20,overflow:'hidden',boxShadow:'0 20px 60px var(--shadow)' }}>
            <div style={{ background:'var(--muted)',padding:'12px 16px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:7 }}>
              {['#FF5F57','#FFBD2E','#28C840'].map(c=><div key={c} style={{ width:10,height:10,borderRadius:'50%',background:c }}/>)}
              <div style={{ flex:1,background:'var(--border)',borderRadius:6,padding:'3px 12px',marginLeft:8,fontSize:11,color:'var(--dim)',textAlign:'center' }}>nyayaflow.app/chat</div>
            </div>
            <div style={{ padding:20,display:'flex',flexDirection:'column',gap:14 }}>
              <div style={{ display:'flex',justifyContent:'flex-end' }}>
                <div style={{ background:'var(--blue)',color:'white',borderRadius:'14px 14px 4px 14px',padding:'10px 15px',fontSize:13,fontWeight:500,maxWidth:'78%' }}>
                  What are my rights if I receive a defective product?
                </div>
              </div>
              <div style={{ display:'flex',gap:10 }}>
                <div style={{ width:30,height:30,borderRadius:8,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
                  <Scale size={14} color="white"/>
                </div>
                <div>
                  <div style={{ display:'inline-flex',alignItems:'center',gap:5,background:'var(--greenLight)',border:'1px solid rgba(16,185,129,0.3)',borderRadius:9999,padding:'2px 10px',marginBottom:7,fontSize:11,color:'var(--green)',fontWeight:600 }}>
                    <Zap size={9}/>From database · 1 token used
                  </div>
                  <div style={{ background:'var(--muted)',border:'1px solid var(--border)',borderRadius:'4px 12px 12px 12px',padding:'12px 14px',fontSize:13,color:'var(--sub)',lineHeight:1.7,maxWidth:'90%' }}>
                    Under <strong style={{ color:'var(--text)' }}>Section 2(9) of the Consumer Protection Act, 2019</strong>, you have the right to seek replacement, refund, or compensation…
                  </div>
                </div>
              </div>
              <div style={{ background:'var(--muted)',border:'1px solid var(--border)',borderRadius:10,padding:'10px 14px',display:'flex',alignItems:'center',gap:10 }}>
                <span style={{ fontSize:13,color:'var(--dim)',flex:1 }}>Ask any legal question…</span>
                <div style={{ width:30,height:30,borderRadius:8,background:'var(--blue)',display:'flex',alignItems:'center',justifyContent:'center' }}>
                  <ArrowRight size={14} color="white"/>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section style={{ background:'var(--blue)',padding:'14px 0',overflow:'hidden' }}>
        <div style={{ display:'flex',animation:'scroll 22s linear infinite',width:'max-content' }}>
          {[...useCases,...useCases].map((u,i)=>(
            <span key={i} style={{ display:'inline-flex',alignItems:'center',gap:12,padding:'0 28px',fontSize:13,color:'rgba(255,255,255,.85)',fontWeight:500,whiteSpace:'nowrap' }}>
              <span style={{ width:4,height:4,borderRadius:'50%',background:'var(--amber)',flexShrink:0 }}/>{u}
            </span>
          ))}
        </div>
      </section>

      <section style={{ maxWidth:1100,margin:'0 auto',padding:'80px 48px' }}>
        <div style={{ textAlign:'center',marginBottom:56 }}>
          <h2 style={{ fontFamily:'"Fraunces"',fontWeight:700,fontSize:38,letterSpacing:'-0.02em',color:'var(--text)',marginBottom:12 }}>Built differently.</h2>
          <p style={{ fontSize:16,color:'var(--sub)',maxWidth:460,margin:'0 auto',lineHeight:1.7 }}>Not a generic chatbot. A self-learning legal intelligence system.</p>
        </div>
        <div style={{ display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:20 }}>
          {features.map(({icon:Icon,title,desc})=>(
            <div key={title} style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:16,padding:28,transition:'all .2s',cursor:'default' }}
              onMouseEnter={e=>{e.currentTarget.style.borderColor='rgba(59,91,219,0.4)';e.currentTarget.style.transform='translateY(-2px)'}}
              onMouseLeave={e=>{e.currentTarget.style.borderColor='var(--border)';e.currentTarget.style.transform='translateY(0)'}}>
              <div style={{ width:42,height:42,borderRadius:11,background:'var(--blueLight)',border:'1px solid rgba(59,91,219,0.2)',display:'flex',alignItems:'center',justifyContent:'center',marginBottom:16 }}>
                <Icon size={20} color="var(--blue)"/>
              </div>
              <h3 style={{ fontWeight:700,fontSize:16,color:'var(--text)',marginBottom:8 }}>{title}</h3>
              <p style={{ fontSize:14,color:'var(--sub)',lineHeight:1.7 }}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section style={{ background:'var(--surface)',borderTop:'1px solid var(--border)',padding:'72px 48px',textAlign:'center',transition:'background .2s' }}>
        <div style={{ maxWidth:540,margin:'0 auto' }}>
          <h2 style={{ fontFamily:'"Fraunces"',fontWeight:700,fontSize:36,letterSpacing:'-0.02em',color:'var(--text)',marginBottom:12 }}>Start for free today</h2>
          <p style={{ fontSize:15,color:'var(--sub)',marginBottom:32,lineHeight:1.7 }}>100 free tokens on signup. No credit card needed.</p>
          <button onClick={()=>nav(user?'/chat':'/register')} style={{ display:'inline-flex',alignItems:'center',gap:8,background:'var(--blue)',color:'white',border:'none',borderRadius:10,padding:'13px 32px',fontSize:15,fontWeight:700,cursor:'pointer' }}>
            <Sparkles size={16}/>{user?'Go to App':'Try NyayaFlow Free'}
          </button>
        </div>
      </section>

      <footer style={{ background:'var(--text)',padding:'24px 48px',display:'flex',alignItems:'center',justifyContent:'space-between' }}>
        <span style={{ fontWeight:800,fontSize:15,color:'var(--bg)' }}>Nyaya<span style={{ color:'var(--amber)' }}>Flow</span></span>
        <p style={{ fontSize:12,color:'var(--dim)' }}>AI-generated legal info · Not a substitute for professional legal advice</p>
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <div style={{ height:'100%',display:'flex',flexDirection:'column' }}>
      <Routes>
        <Route path="/"         element={<Landing/>}/>
        <Route path="/login"    element={<AuthPage mode="login"/>}/>
        <Route path="/register" element={<AuthPage mode="register"/>}/>
        <Route path="/chat"     element={<Protected><div style={{height:'100%',display:'flex',flexDirection:'column'}}><Nav/><div style={{flex:1,overflow:'hidden'}}><ChatPage/></div></div></Protected>}/>
        <Route path="/docs"     element={<Protected><div style={{height:'100%',display:'flex',flexDirection:'column'}}><Nav/><div style={{flex:1,overflow:'hidden'}}><DocBuilderPage/></div></div></Protected>}/>
      </Routes>
    </div>
  )
}