import { useState, useEffect } from 'react'
import { X, Zap, Loader2 } from 'lucide-react'
import { getTokenPlans, createOrder, verifyPayment } from '../api'
import { useAuth } from '../context/AuthContext'

export default function TokenModal({ onClose }) {
  const [plans,    setPlans]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [ordering, setOrdering] = useState('')
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState('')
  const { user, updateTokens }  = useAuth()

  useEffect(() => {
    getTokenPlans().then(data => { setPlans(data.plans); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const handlePurchase = async (plan) => {
    setError(''); setOrdering(plan.id)
    try {
      const order = await createOrder(plan.id)
      await new Promise((res, rej) => {
        if (window.Razorpay) { res(); return }
        const s = document.createElement('script')
        s.src = 'https://checkout.razorpay.com/v1/checkout.js'
        s.onload = res; s.onerror = rej
        document.head.appendChild(s)
      })
      const rzp = new window.Razorpay({
        key:         order.key_id,
        amount:      order.amount,
        currency:    order.currency,
        name:        'NyayaFlow',
        description: `${plan.tokens} Tokens — ${plan.label}`,
        order_id:    order.order_id,
        prefill:     { name: order.user_name, email: order.user_email },
        theme:       { color: '#3B5BDB' },
        handler: async (response) => {
          try {
            const result = await verifyPayment({
              razorpay_order_id:   response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature:  response.razorpay_signature,
            })
            updateTokens(result.new_balance)
            setSuccess(`✅ ${result.tokens_purchased} tokens added! New balance: ${result.new_balance}`)
          } catch (e) {
            setError(e.response?.data?.error || 'Payment verification failed.')
          }
        },
        modal: { ondismiss: () => setOrdering('') },
      })
      rzp.open()
    } catch (e) {
      setError(e.response?.data?.error || 'Could not create order.')
      setOrdering('')
    }
  }

  return (
    <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.6)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:1000,padding:20 }}>
      <div style={{ background:'var(--surface)',borderRadius:20,width:'100%',maxWidth:520,boxShadow:'0 24px 64px rgba(0,0,0,0.25)',fontFamily:'"Plus Jakarta Sans"',border:'1px solid var(--border)' }}>
        <div style={{ padding:'20px 24px 16px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',justifyContent:'space-between' }}>
          <div>
            <h2 style={{ fontFamily:'"Fraunces"',fontWeight:700,fontSize:22,color:'var(--text)',marginBottom:2 }}>Buy Tokens</h2>
            <p style={{ fontSize:13,color:'var(--sub)' }}>Current balance: <strong style={{ color:'var(--blue)' }}>{user?.tokens || 0} tokens</strong></p>
          </div>
          <button onClick={onClose} style={{ background:'none',border:'none',cursor:'pointer',color:'var(--dim)',padding:4 }}>
            <X size={20}/>
          </button>
        </div>

        <div style={{ padding:'14px 24px',background:'var(--muted)',borderBottom:'1px solid var(--border)',display:'flex',gap:24,flexWrap:'wrap' }}>
          <div style={{ display:'flex',alignItems:'center',gap:7,fontSize:13,color:'var(--sub)' }}>
            <Zap size={13} color="var(--blue)"/><span><strong style={{ color:'var(--text)' }}>1 token</strong> per chat query</span>
          </div>
          <div style={{ display:'flex',alignItems:'center',gap:7,fontSize:13,color:'var(--sub)' }}>
            <Zap size={13} color="var(--amber)"/><span><strong style={{ color:'var(--text)' }}>10 tokens</strong> per PDF document</span>
          </div>
        </div>

        <div style={{ padding:'20px 24px' }}>
          {loading ? (
            <div style={{ textAlign:'center',padding:32,color:'var(--dim)' }}>Loading plans…</div>
          ) : (
            <div style={{ display:'flex',flexDirection:'column',gap:10 }}>
              {plans.map(plan => (
                <div key={plan.id} style={{ display:'flex',alignItems:'center',justifyContent:'space-between',padding:'14px 16px',
                  border:`1px solid ${plan.popular?'rgba(59,91,219,0.4)':'var(--border)'}`,
                  borderRadius:12,
                  background:plan.popular?'var(--blueLight)':'var(--surface)',
                  transition:'all .15s',position:'relative' }}>
                  {plan.popular && (
                    <div style={{ position:'absolute',top:-10,left:16,background:'var(--blue)',color:'white',fontSize:10,fontWeight:700,padding:'2px 10px',borderRadius:9999 }}>MOST POPULAR</div>
                  )}
                  <div>
                    <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:2 }}>
                      <span style={{ fontWeight:700,fontSize:15,color:'var(--text)' }}>{plan.label}</span>
                      <span style={{ fontSize:13,fontWeight:700,color:'var(--blue)' }}>{plan.tokens} tokens</span>
                    </div>
                    <p style={{ fontSize:12,color:'var(--dim)' }}>{plan.description}</p>
                  </div>
                  <button onClick={()=>handlePurchase(plan)} disabled={!!ordering}
                    style={{ padding:'8px 18px',borderRadius:9,
                      background:plan.popular?'var(--blue)':'var(--surface)',
                      color:plan.popular?'white':'var(--text)',
                      border:`1px solid ${plan.popular?'var(--blue)':'var(--border)'}`,
                      fontSize:13,fontWeight:700,cursor:ordering?'not-allowed':'pointer',transition:'all .15s',display:'flex',alignItems:'center',gap:6,whiteSpace:'nowrap',opacity:ordering?.7:1 }}>
                    {ordering===plan.id ? <Loader2 size={13} className="spin"/> : null}
                    ₹{(plan.price_paise/100).toFixed(0)}
                  </button>
                </div>
              ))}
            </div>
          )}

          {error   && <div style={{ marginTop:14,padding:'9px 12px',background:'rgba(220,38,38,0.08)',border:'1px solid rgba(220,38,38,0.2)',borderRadius:9,fontSize:13,color:'#EF4444' }}>{error}</div>}
          {success && <div style={{ marginTop:14,padding:'9px 12px',background:'var(--greenLight)',border:'1px solid rgba(16,185,129,0.3)',borderRadius:9,fontSize:13,color:'var(--green)',fontWeight:500 }}>{success}</div>}

          <p style={{ marginTop:16,fontSize:11,color:'var(--dim)',textAlign:'center' }}>
            Secured by Razorpay · UPI, Cards, Net Banking accepted
          </p>
        </div>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}