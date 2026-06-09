import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scale, Mail, Lock, User, ArrowRight, Eye, EyeOff } from 'lucide-react'
import { register, login } from '../api'
import { useAuth } from '../context/AuthContext'

export default function AuthPage({ mode = 'login' }) {
  const [isLogin,  setIsLogin]  = useState(mode === 'login')
  const [name,     setName]     = useState('')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPwd,  setShowPwd]  = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  const { signIn } = useAuth()
  const navigate   = useNavigate()

  const handleSubmit = async () => {
    setError('')
    if (!email || !password || (!isLogin && !name)) { setError('Please fill in all fields.'); return }
    setLoading(true)
    try {
      const data = isLogin ? await login(email, password) : await register(name, email, password)
      signIn(data.access_token, data.user)
      navigate('/chat')
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong. Try again.')
    } finally { setLoading(false) }
  }

  const iStyle = {
    width:'100%', background:'var(--muted)', border:'1px solid var(--border)',
    color:'var(--text)', fontFamily:'"Plus Jakarta Sans"', fontSize:14,
    padding:'11px 14px 11px 42px', borderRadius:10, outline:'none', transition:'all .15s',
  }

  return (
    <div style={{ minHeight:'100vh', background:'var(--bg)', display:'flex', alignItems:'center', justifyContent:'center', padding:24, fontFamily:'"Plus Jakarta Sans"' }}>
      <div style={{ width:'100%', maxWidth:420 }}>
        <div style={{ textAlign:'center', marginBottom:32 }}>
          <div style={{ width:48,height:48,borderRadius:14,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'inline-flex',alignItems:'center',justifyContent:'center',marginBottom:12 }}>
            <Scale size={22} color="white"/>
          </div>
          <h1 style={{ fontFamily:'"Fraunces"',fontWeight:700,fontSize:26,letterSpacing:'-0.02em',color:'var(--text)',marginBottom:6 }}>
            {isLogin ? 'Welcome back' : 'Join NyayaFlow'}
          </h1>
          <p style={{ fontSize:14,color:'var(--sub)' }}>
            {isLogin ? 'Sign in to continue your legal research' : 'Get 100 free tokens to start'}
          </p>
        </div>

        <div style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:16,padding:28,boxShadow:'0 4px 24px rgba(59,91,219,0.06)' }}>
          <div style={{ display:'flex',background:'var(--muted)',borderRadius:10,padding:3,marginBottom:24 }}>
            {['Login','Sign Up'].map((label,i) => (
              <button key={label} onClick={()=>{setIsLogin(i===0);setError('')}}
                style={{ flex:1,padding:'7px',borderRadius:8,fontSize:13,fontWeight:600,cursor:'pointer',transition:'all .15s',border:'none',
                  background:((i===0)===isLogin)?'var(--surface)':'transparent',
                  color:((i===0)===isLogin)?'var(--text)':'var(--dim)',
                  boxShadow:((i===0)===isLogin)?'0 1px 4px rgba(0,0,0,0.08)':'none' }}>
                {label}
              </button>
            ))}
          </div>

          <div style={{ display:'flex',flexDirection:'column',gap:14 }}>
            {!isLogin && (
              <div style={{ position:'relative' }}>
                <User size={16} style={{ position:'absolute',left:13,top:'50%',transform:'translateY(-50%)',color:'var(--dim)',pointerEvents:'none' }}/>
                <input value={name} onChange={e=>setName(e.target.value)} placeholder="Full name" style={iStyle}
                  onFocus={e=>{e.target.style.borderColor='rgba(59,91,219,0.5)';e.target.style.boxShadow='0 0 0 3px rgba(59,91,219,0.1)'}}
                  onBlur={e=>{e.target.style.borderColor='var(--border)';e.target.style.boxShadow='none'}}/>
              </div>
            )}
            <div style={{ position:'relative' }}>
              <Mail size={16} style={{ position:'absolute',left:13,top:'50%',transform:'translateY(-50%)',color:'var(--dim)',pointerEvents:'none' }}/>
              <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email address" style={iStyle}
                onFocus={e=>{e.target.style.borderColor='rgba(59,91,219,0.5)';e.target.style.boxShadow='0 0 0 3px rgba(59,91,219,0.1)'}}
                onBlur={e=>{e.target.style.borderColor='var(--border)';e.target.style.boxShadow='none'}}
                onKeyDown={e=>e.key==='Enter'&&handleSubmit()}/>
            </div>
            <div style={{ position:'relative' }}>
              <Lock size={16} style={{ position:'absolute',left:13,top:'50%',transform:'translateY(-50%)',color:'var(--dim)',pointerEvents:'none' }}/>
              <input type={showPwd?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" style={{ ...iStyle,paddingRight:42 }}
                onFocus={e=>{e.target.style.borderColor='rgba(59,91,219,0.5)';e.target.style.boxShadow='0 0 0 3px rgba(59,91,219,0.1)'}}
                onBlur={e=>{e.target.style.borderColor='var(--border)';e.target.style.boxShadow='none'}}
                onKeyDown={e=>e.key==='Enter'&&handleSubmit()}/>
              <button onClick={()=>setShowPwd(p=>!p)} style={{ position:'absolute',right:12,top:'50%',transform:'translateY(-50%)',background:'none',border:'none',cursor:'pointer',color:'var(--dim)',padding:2 }}>
                {showPwd?<EyeOff size={15}/>:<Eye size={15}/>}
              </button>
            </div>
          </div>

          {error && (
            <div style={{ marginTop:14,padding:'9px 12px',background:'rgba(220,38,38,0.08)',border:'1px solid rgba(220,38,38,0.2)',borderRadius:9,fontSize:13,color:'#EF4444',fontWeight:500 }}>
              {error}
            </div>
          )}

          <button onClick={handleSubmit} disabled={loading}
            style={{ width:'100%',marginTop:20,padding:'12px',borderRadius:10,background:'var(--blue)',color:'white',border:'none',fontSize:14,fontWeight:700,cursor:loading?'not-allowed':'pointer',transition:'all .15s',display:'flex',alignItems:'center',justifyContent:'center',gap:8,opacity:loading?.7:1 }}>
            {loading
              ? <span style={{ width:16,height:16,border:'2px solid rgba(255,255,255,.3)',borderTopColor:'white',borderRadius:'50%' }} className="spin"/>
              : <>{isLogin?'Sign In':'Create Account'}<ArrowRight size={15}/></>
            }
          </button>

          {!isLogin && (
            <p style={{ textAlign:'center',fontSize:12,color:'var(--dim)',marginTop:14 }}>
              🎁 New accounts get <strong style={{ color:'var(--blue)' }}>100 free tokens</strong> — no credit card needed
            </p>
          )}
        </div>

        <p style={{ textAlign:'center',fontSize:12,color:'var(--dim)',marginTop:20 }}>
          Answers are AI-generated and not a substitute for legal advice.
        </p>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}