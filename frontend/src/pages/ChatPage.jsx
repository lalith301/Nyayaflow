import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Scale, BookOpen, Globe, Zap, Plus, Clock, MessageSquare } from 'lucide-react'
import { sendChatMessage, getChatHistory } from '../api'
import { useAuth } from '../context/AuthContext'
import VoiceMicButton from '../components/VoiceMicButton'

const SUGGESTIONS = [
  { text:"What are my rights if I receive a defective product?", tag:"Consumer", color:'#7C3AED' },
  { text:"What is the punishment for cybercrime in India?",       tag:"IT Law",  color:'#0891B2' },
  { text:"Can a landlord evict me without notice in Tamil Nadu?", tag:"Property",color:'#059669' },
  { text:"How do I file an RTI application?",                     tag:"RTI",     color:'#D97706' },
  { text:"What constitutes a valid contract in India?",           tag:"Contract",color:'#DC2626' },
  { text:"What are motor vehicle insurance rules in India?",      tag:"MV Act",  color:'#2563EB' },
]

function cleanSrc(s) {
  return s.split('/').pop().replace('.pdf','').replace(/_/g,' ')
    .replace(/\b\w/g,l=>l.toUpperCase()).slice(0,32)
}

function groupByDate(messages) {
  const groups = {}
  messages.forEach(m => {
    if (m.role !== 'user') return
    const date = new Date(m.created_at)
    const key  = date.toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })
    if (!groups[key]) groups[key] = []
    groups[key].push({ id: m.id, title: m.content.slice(0,38)+'…', time: date.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' }) })
  })
  return groups
}

function Message({ msg }) {
  if (msg.role === 'user') return (
    <div className="msg-in" style={{ display:'flex', justifyContent:'flex-end' }}>
      <div style={{ maxWidth:'72%', background:'var(--blue)', color:'white', borderRadius:'16px 16px 4px 16px', padding:'11px 16px', fontSize:14, lineHeight:1.6, fontWeight:500 }}>
        {msg.content}
      </div>
    </div>
  )

  if (msg.role === 'typing') return (
    <div className="msg-in" style={{ display:'flex', gap:10, alignItems:'flex-start' }}>
      <div style={{ width:32,height:32,borderRadius:9,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
        <Scale size={15} color="white"/>
      </div>
      <div style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:10,padding:'12px 16px',display:'flex',alignItems:'center',gap:8 }}>
        {msg.isAgent
          ? <span style={{ fontSize:13,color:'var(--amber)',display:'flex',alignItems:'center',gap:6,fontWeight:500 }}><Globe size={12}/>Fetching from indiacode.nic.in…</span>
          : <><span className="dot"/><span className="dot"/><span className="dot"/></>
        }
      </div>
    </div>
  )

  return (
    <div className="msg-in" style={{ display:'flex', gap:10, alignItems:'flex-start' }}>
      <div style={{ width:32,height:32,borderRadius:9,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
        <Scale size={15} color="white"/>
      </div>
      <div style={{ flex:1, minWidth:0, maxWidth:'88%' }}>
        {msg.usedAgent && msg.lawFetched
          ? <div style={{ display:'inline-flex',alignItems:'center',gap:5,background:'var(--amberLight)',border:'1px solid rgba(245,158,11,0.4)',borderRadius:9999,padding:'3px 10px',marginBottom:8,fontSize:11,color:'var(--amberDark)',fontWeight:600 }}>
              <Globe size={9}/>Fetched live · {msg.lawFetched} · saved
            </div>
          : <div style={{ display:'inline-flex',alignItems:'center',gap:5,background:'var(--greenLight)',border:'1px solid rgba(16,185,129,0.3)',borderRadius:9999,padding:'3px 10px',marginBottom:8,fontSize:11,color:'var(--green)',fontWeight:600 }}>
              <Zap size={9}/>From database
            </div>
        }
        <div style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:'4px 12px 12px 12px',padding:'14px 16px' }}>
          <p style={{ fontSize:14,lineHeight:1.75,color:'var(--sub)',margin:0,whiteSpace:'pre-wrap' }}>{msg.content}</p>
        </div>
        {msg.sources?.length > 0 && (
          <div style={{ marginTop:8,display:'flex',flexWrap:'wrap',gap:6 }}>
            {msg.sources.map((s,i)=>(
              <div key={i} style={{ display:'inline-flex',alignItems:'center',gap:5,background:'var(--blueLight)',border:'1px solid rgba(59,91,219,0.2)',borderRadius:9999,padding:'3px 10px',fontSize:11,color:'var(--blue)',maxWidth:220 }}>
                <BookOpen size={9} style={{ flexShrink:0 }}/>
                <span style={{ overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>{cleanSrc(s.source)}</span>
                {s.page!=='live'&&<span style={{ color:'var(--dim)',flexShrink:0 }}>·{s.page}</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatPage() {
  const [messages,       setMessages]       = useState([])
  const [input,          setInput]          = useState('')
  const [loading,        setLoading]        = useState(false)
  const [historyGroups,  setHistoryGroups]  = useState({})
  const [historyLoading, setHistoryLoading] = useState(true)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)
  const isEmpty   = messages.length === 0
  const { updateTokens } = useAuth()

  useEffect(() => {
    getChatHistory(100)
      .then(data => { setHistoryGroups(groupByDate(data.messages)); setHistoryLoading(false) })
      .catch(() => setHistoryLoading(false))
  }, [])

  const refreshHistory = useCallback(() => {
    getChatHistory(100).then(data => setHistoryGroups(groupByDate(data.messages))).catch(()=>{})
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }) }, [messages])

  const handleNew = () => { setMessages([]); setInput('') }

  const send = useCallback(async (text) => {
    const q = (text||input).trim()
    if (!q||loading) return
    setInput(''); setLoading(true)
    setMessages(p=>[...p,{ id:Date.now(), role:'user', content:q }])
    const tid = Date.now()+1
    setMessages(p=>[...p,{ id:tid, role:'typing', isAgent:false }])
    const t = setTimeout(()=>setMessages(p=>p.map(m=>m.id===tid?{...m,isAgent:true}:m)), 3000)
    try {
      const r = await sendChatMessage(q)
      clearTimeout(t)
      setMessages(p=>[...p.filter(m=>m.id!==tid),{
        id:Date.now()+2, role:'assistant',
        content:r.answer, sources:r.sources||[],
        usedAgent:r.used_agent, lawFetched:r.law_fetched,
      }])
      if (r.tokens_remaining !== undefined) updateTokens(r.tokens_remaining)
      refreshHistory()
    } catch(e) {
      clearTimeout(t)
      const errMsg = e.response?.status === 402
        ? `⚠️ ${e.response.data.error} You have ${e.response.data.tokens_have} tokens.`
        : e.response?.data?.error || 'Could not reach server. Is Flask running on port 8000?'
      setMessages(p=>[...p.filter(m=>m.id!==tid),{ id:Date.now()+2, role:'assistant', content:errMsg, sources:[], isError:true }])
    } finally { setLoading(false); inputRef.current?.focus() }
  }, [input, loading, updateTokens, refreshHistory])

  const dateKeys = Object.keys(historyGroups)

  return (
    <div style={{ height:'100%', display:'flex', overflow:'hidden', background:'var(--bg)' }}>
      {/* Sidebar */}
      <div style={{ width:220,flexShrink:0,background:'var(--surface)',borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column' }}>
        <div style={{ padding:12, borderBottom:'1px solid var(--border)' }}>
          <button onClick={handleNew}
            style={{ width:'100%',display:'flex',alignItems:'center',justifyContent:'center',gap:7,background:'var(--blueLight)',color:'var(--blue)',border:'1px solid rgba(59,91,219,0.25)',borderRadius:9,padding:'8px',fontSize:13,fontFamily:'"Plus Jakarta Sans"',fontWeight:600,cursor:'pointer',transition:'all .15s' }}
            onMouseEnter={e=>{e.currentTarget.style.background='var(--blue)';e.currentTarget.style.color='white'}}
            onMouseLeave={e=>{e.currentTarget.style.background='var(--blueLight)';e.currentTarget.style.color='var(--blue)'}}>
            <Plus size={13}/>New Chat
          </button>
        </div>

        <div style={{ flex:1,overflowY:'auto',padding:8 }}>
          {historyLoading ? (
            <p style={{ fontSize:12,color:'var(--dim)',padding:8,textAlign:'center' }}>Loading history…</p>
          ) : dateKeys.length === 0 ? (
            <div style={{ padding:'24px 8px',textAlign:'center' }}>
              <MessageSquare size={24} style={{ color:'var(--border)',margin:'0 auto 8px',display:'block' }}/>
              <p style={{ fontSize:12,color:'var(--dim)' }}>No chats yet.<br/>Ask your first question!</p>
            </div>
          ) : (
            dateKeys.map(date => (
              <div key={date} style={{ marginBottom:12 }}>
                <p style={{ fontSize:10,color:'var(--dim)',fontWeight:700,padding:'4px 8px',textTransform:'uppercase',letterSpacing:'0.08em' }}>{date}</p>
                {historyGroups[date].map(chat => (
                  <div key={chat.id}
                    style={{ padding:'8px 10px',borderRadius:8,cursor:'pointer',marginBottom:2,border:'1px solid transparent',transition:'all .12s' }}
                    onMouseEnter={e=>{e.currentTarget.style.background='var(--muted)';e.currentTarget.style.borderColor='var(--border)'}}
                    onMouseLeave={e=>{e.currentTarget.style.background='transparent';e.currentTarget.style.borderColor='transparent'}}>
                    <p style={{ fontSize:12,color:'var(--sub)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',marginBottom:3,fontWeight:500 }}>{chat.title}</p>
                    <span style={{ fontSize:10,color:'var(--dim)',display:'flex',alignItems:'center',gap:4 }}><Clock size={9}/>{chat.time}</span>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        <div style={{ padding:12,borderTop:'1px solid var(--border)',background:'var(--muted)' }}>
          <p style={{ fontSize:11,color:'var(--dim)',textAlign:'center',lineHeight:1.6 }}>Grounded in official<br/>Indian legal corpus</p>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex:1,display:'flex',flexDirection:'column',minWidth:0 }}>
        {isEmpty && (
          <div className="fade-in" style={{ flex:1,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:'40px 24px' }}>
            <div style={{ width:56,height:56,borderRadius:16,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'flex',alignItems:'center',justifyContent:'center',marginBottom:20 }}>
              <Scale size={26} color="white"/>
            </div>
            <h1 style={{ fontFamily:'"Fraunces"',fontWeight:700,fontSize:28,letterSpacing:'-0.02em',color:'var(--text)',marginBottom:8,textAlign:'center' }}>
              Ask any legal question
            </h1>
            <p style={{ fontSize:14,color:'var(--sub)',textAlign:'center',maxWidth:400,lineHeight:1.6,marginBottom:36 }}>
              Plain English or Hindi. Grounded in Indian law. Unknown acts fetched automatically.
            </p>
            <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:10,maxWidth:640,width:'100%' }}>
              {SUGGESTIONS.map((s,i)=>(
                <button key={i} onClick={()=>send(s.text)}
                  style={{ textAlign:'left',padding:'14px 16px',background:'var(--surface)',border:'1px solid var(--border)',borderRadius:12,cursor:'pointer',transition:'all .15s' }}
                  onMouseEnter={e=>{e.currentTarget.style.borderColor='rgba(59,91,219,0.4)';e.currentTarget.style.transform='translateY(-1px)'}}
                  onMouseLeave={e=>{e.currentTarget.style.borderColor='var(--border)';e.currentTarget.style.transform='translateY(0)'}}>
                  <span style={{ display:'inline-block',fontSize:10,fontWeight:700,padding:'2px 8px',borderRadius:9999,marginBottom:7,background:s.color+'20',color:s.color,border:`1px solid ${s.color}44` }}>
                    {s.tag}
                  </span>
                  <p style={{ fontSize:13,color:'var(--sub)',lineHeight:1.5,margin:0,fontWeight:500 }}>{s.text}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {!isEmpty && (
          <div style={{ flex:1,overflowY:'auto',padding:'24px',display:'flex',flexDirection:'column',gap:18,maxWidth:800,width:'100%',margin:'0 auto' }}>
            {messages.map(m=><Message key={m.id} msg={m}/>)}
            <div ref={bottomRef}/>
          </div>
        )}

        {/* Input */}
        <div style={{ borderTop:'1px solid var(--border)',background:'var(--surface)',padding:'12px 20px' }}>
          <div style={{ maxWidth:800,margin:'0 auto',display:'flex',gap:8,alignItems:'flex-end' }}>
            <div style={{ flex:1,background:'var(--muted)',border:'1px solid var(--border)',borderRadius:12,overflow:'hidden',transition:'all .15s' }}
              onFocusCapture={e=>{e.currentTarget.style.borderColor='rgba(59,91,219,0.5)';e.currentTarget.style.boxShadow='0 0 0 3px rgba(59,91,219,0.1)'}}
              onBlurCapture={e=>{e.currentTarget.style.borderColor='var(--border)';e.currentTarget.style.boxShadow='none'}}>
              <textarea ref={inputRef} value={input} onChange={e=>setInput(e.target.value)}
                onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}
                placeholder="Ask any legal question — unknown laws fetched automatically…"
                rows={1} disabled={loading}
                style={{ width:'100%',background:'transparent',border:'none',outline:'none',padding:'11px 14px',fontSize:14,color:'var(--text)',fontFamily:'"Plus Jakarta Sans"',resize:'none',lineHeight:1.5,minHeight:44,maxHeight:120,display:'block' }}
                onInput={e=>{e.target.style.height='auto';e.target.style.height=Math.min(e.target.scrollHeight,120)+'px'}}
              />
            </div>
            <VoiceMicButton onTranscribed={t=>{setInput(t);inputRef.current?.focus()}} disabled={loading}/>
            <button onClick={()=>send()} disabled={!input.trim()||loading}
              style={{ height:44,padding:'0 20px',borderRadius:11,background:input.trim()&&!loading?'var(--blue)':'var(--muted)',color:input.trim()&&!loading?'white':'var(--dim)',border:`1px solid ${input.trim()&&!loading?'var(--blue)':'var(--border)'}`,fontFamily:'"Plus Jakarta Sans"',fontWeight:700,fontSize:13,cursor:input.trim()&&!loading?'pointer':'not-allowed',transition:'all .2s',display:'flex',alignItems:'center',gap:7,flexShrink:0 }}>
              {loading?<span style={{ width:14,height:14,border:'2px solid rgba(255,255,255,.3)',borderTopColor:'white',borderRadius:'50%' }} className="spin"/>:<Send size={14}/>}
              Send
            </button>
          </div>
          <p style={{ textAlign:'center',fontSize:11,color:'var(--dim)',marginTop:8 }}>AI-generated · Always verify with a qualified advocate</p>
        </div>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}