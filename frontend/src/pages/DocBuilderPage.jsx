import { useState, useEffect } from 'react'
import { FileText, Download, Loader2, CheckCircle2, ChevronRight, Eye, AlertCircle, Scale } from 'lucide-react'
import { getDocTypes, generateDocument } from '../api'

const DOC_FIELDS = {
  rental_agreement:[
    {key:'landlord_name',label:'Landlord Full Name',placeholder:'e.g. Ramesh Kumar',span:1},
    {key:'tenant_name',label:'Tenant Full Name',placeholder:'e.g. Priya Sharma',span:1},
    {key:'property_address',label:'Property Address',placeholder:'12, Anna Nagar, Chennai 600040',span:2,textarea:true},
    {key:'monthly_rent',label:'Monthly Rent (₹)',placeholder:'25000',span:1,type:'number'},
    {key:'security_deposit',label:'Security Deposit (₹)',placeholder:'50000',span:1,type:'number'},
    {key:'start_date',label:'Start Date',placeholder:'01 August 2025',span:1},
    {key:'duration_months',label:'Duration (months)',placeholder:'11',span:1,type:'number'},
    {key:'state',label:'State / UT',placeholder:'Tamil Nadu',span:1},
  ],
  nda:[
    {key:'disclosing_party',label:'Disclosing Party',placeholder:'Company sharing info',span:1},
    {key:'receiving_party',label:'Receiving Party',placeholder:'Company receiving info',span:1},
    {key:'purpose',label:'Purpose',placeholder:'Evaluation of partnership…',span:2,textarea:true},
    {key:'duration_years',label:'Duration (years)',placeholder:'3',span:1,type:'number'},
    {key:'jurisdiction',label:'Jurisdiction',placeholder:'Mumbai',span:1},
  ],
  freelance_contract:[
    {key:'client_name',label:'Client Name',placeholder:'Acme Tech Pvt Ltd',span:1},
    {key:'freelancer_name',label:'Freelancer Name',placeholder:'Arun Subramanian',span:1},
    {key:'scope_of_work',label:'Scope of Work',placeholder:'Describe deliverables…',span:2,textarea:true},
    {key:'project_fee',label:'Project Fee (₹)',placeholder:'80000',span:1,type:'number'},
    {key:'payment_terms',label:'Payment Terms',placeholder:'50% advance, 50% on delivery',span:1},
    {key:'timeline',label:'Timeline',placeholder:'30 days from signing',span:2},
  ],
  employment_offer:[
    {key:'company_name',label:'Company Name',placeholder:'TechVentures India Pvt Ltd',span:1},
    {key:'candidate_name',label:'Candidate Name',placeholder:'Kavya Nair',span:1},
    {key:'position',label:'Position',placeholder:'Senior Software Engineer',span:2},
    {key:'annual_ctc',label:'Annual CTC (₹)',placeholder:'1200000',span:1,type:'number'},
    {key:'joining_date',label:'Joining Date',placeholder:'01 September 2025',span:1},
    {key:'probation_months',label:'Probation (months)',placeholder:'6',span:1,type:'number'},
    {key:'reporting_manager',label:'Reporting Manager',placeholder:'Suresh Babu, VP Eng',span:1},
  ],
  affidavit:[
    {key:'deponent_name',label:"Deponent's Name",placeholder:'Full name',span:1},
    {key:'deponent_address',label:"Deponent's Address",placeholder:'Full address…',span:2,textarea:true},
    {key:'statement_of_facts',label:'Statement of Facts',placeholder:'State facts clearly…',span:2,textarea:true},
    {key:'purpose',label:'Purpose',placeholder:'For passport application',span:1},
    {key:'location',label:'Place of Signing',placeholder:'Chennai, Tamil Nadu',span:1},
    {key:'date',label:'Date',placeholder:'15 July 2025',span:1},
  ],
}

export default function DocBuilderPage() {
  const [docTypes,setDocTypes]=useState({})
  const [sel,setSel]=useState('')
  const [fields,setFields]=useState({})
  const [loading,setLoading]=useState(false)
  const [done,setDone]=useState(false)
  const [error,setError]=useState('')
  const [fetching,setFetching]=useState(true)

  useEffect(()=>{
    getDocTypes().then(t=>{setDocTypes(t);setFetching(false)}).catch(()=>{
      setDocTypes({rental_agreement:'Residential Rental Agreement',nda:'Non-Disclosure Agreement',freelance_contract:'Freelance Service Agreement',employment_offer:'Employment Offer Letter',affidavit:'General Affidavit'})
      setFetching(false)
    })
  },[])

  const cf=DOC_FIELDS[sel]||[]
  const filled=cf.filter(f=>(fields[f.key]||'').trim()).length
  const allFilled=filled===cf.length&&cf.length>0
  const pct=cf.length?(filled/cf.length)*100:0

  const generate=async()=>{
    if(!allFilled){setError('Fill all fields first.');return}
    setError('');setLoading(true);setDone(false)
    try{await generateDocument(sel,fields);setDone(true)}
    catch(e){setError(e.response?.data?.error||'Generation failed.')}
    finally{setLoading(false)}
  }

  const iStyle={
    width:'100%',
    background:'var(--surface)',
    border:'1px solid var(--border)',
    color:'var(--text)',
    fontFamily:'"Plus Jakarta Sans"',
    fontSize:13,
    padding:'9px 12px',
    borderRadius:9,
    outline:'none',
    transition:'all .15s',
  }

  return (
    <div style={{height:'100%',display:'flex',overflow:'hidden',background:'var(--bg)'}}>
      {/* Doc type list */}
      <div style={{width:200,flexShrink:0,background:'var(--surface)',borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column'}}>
        <div style={{padding:'12px 12px 8px',borderBottom:'1px solid var(--border)'}}>
          <p style={{fontSize:10,color:'var(--dim)',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.08em'}}>Document Type</p>
        </div>
        <div style={{flex:1,overflowY:'auto',padding:8}}>
          {fetching ? <p style={{fontSize:12,color:'var(--dim)',padding:8}}>Loading…</p>
          : Object.entries(docTypes).map(([key,label])=>(
            <button key={key} onClick={()=>{setSel(key);setFields({});setDone(false);setError('')}}
              style={{width:'100%',textAlign:'left',padding:'8px 10px',borderRadius:9,fontSize:12,fontFamily:'"Plus Jakarta Sans"',cursor:'pointer',transition:'all .12s',marginBottom:3,display:'flex',alignItems:'center',justifyContent:'space-between',fontWeight:500,
                background:sel===key?'var(--blueLight)':'transparent',
                color:sel===key?'var(--blue)':'var(--sub)',
                border:`1px solid ${sel===key?'rgba(59,91,219,0.3)':'transparent'}`
              }}
              onMouseEnter={e=>{if(sel!==key){e.currentTarget.style.background='var(--muted)';e.currentTarget.style.color='var(--text)'}}}
              onMouseLeave={e=>{if(sel!==key){e.currentTarget.style.background='transparent';e.currentTarget.style.color='var(--sub)'}}}>
              {label}{sel===key&&<ChevronRight size={11}/>}
            </button>
          ))}
        </div>
      </div>

      {/* Form */}
      <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
        <div style={{padding:'10px 20px',borderBottom:'1px solid var(--border)',background:'var(--surface)',display:'flex',alignItems:'center',gap:8}}>
          <FileText size={13} style={{color:'var(--blue)'}}/>
          <span style={{fontSize:12,fontFamily:'"Plus Jakarta Sans"',fontWeight:700,color:'var(--sub)',textTransform:'uppercase',letterSpacing:'0.06em'}}>
            {sel?docTypes[sel]:'Select a document type'}
          </span>
          {sel&&<span style={{fontSize:11,color:'var(--dim)',marginLeft:'auto'}}>{filled}/{cf.length} fields</span>}
        </div>

        {!sel ? (
          <div style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:14,padding:32}}>
            <div style={{width:52,height:52,borderRadius:14,background:'linear-gradient(135deg,var(--blue),var(--blueMid))',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <FileText size={24} color="white"/>
            </div>
            <h2 style={{fontFamily:'"Fraunces"',fontWeight:700,fontSize:22,color:'var(--text)',letterSpacing:'-0.02em'}}>Draft a Legal Document</h2>
            <p style={{fontSize:13,color:'var(--sub)',textAlign:'center',maxWidth:300,lineHeight:1.6}}>AI-generated PDFs for rental agreements, NDAs, offer letters and more</p>
          </div>
        ) : (
          <div style={{flex:1,overflowY:'auto',padding:24}}>
            <div style={{height:4,background:'var(--border)',borderRadius:9999,marginBottom:24,overflow:'hidden'}}>
              <div style={{height:'100%',background:'linear-gradient(90deg,var(--blue),var(--amber))',width:`${pct}%`,transition:'width .4s',borderRadius:9999}}/>
            </div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,maxWidth:580}}>
              {cf.map(f=>(
                <div key={f.key} style={{gridColumn:f.span===2||f.textarea?'span 2':'span 1'}}>
                  <label style={{display:'block',fontSize:11,fontFamily:'"Plus Jakarta Sans"',fontWeight:700,color:'var(--dim)',textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:6}}>{f.label}</label>
                  {f.textarea
                    ? <textarea value={fields[f.key]||''} onChange={e=>setFields(p=>({...p,[f.key]:e.target.value}))} placeholder={f.placeholder} disabled={loading} rows={3} style={{...iStyle,resize:'none'}}
                        onFocus={e=>{e.target.style.borderColor='rgba(59,91,219,0.5)';e.target.style.boxShadow='0 0 0 3px rgba(59,91,219,0.1)'}}
                        onBlur={e=>{e.target.style.borderColor='var(--border)';e.target.style.boxShadow='none'}}/>
                    : <input type={f.type||'text'} value={fields[f.key]||''} onChange={e=>setFields(p=>({...p,[f.key]:e.target.value}))} placeholder={f.placeholder} disabled={loading} style={iStyle}
                        onFocus={e=>{e.target.style.borderColor='rgba(59,91,219,0.5)';e.target.style.boxShadow='0 0 0 3px rgba(59,91,219,0.1)'}}
                        onBlur={e=>{e.target.style.borderColor='var(--border)';e.target.style.boxShadow='none'}}/>
                  }
                </div>
              ))}
            </div>
          </div>
        )}

        {sel && (
          <div style={{padding:'14px 24px',borderTop:'1px solid var(--border)',background:'var(--surface)'}}>
            {error && <div style={{display:'flex',alignItems:'center',gap:7,fontSize:13,color:'#DC2626',background:'rgba(220,38,38,0.08)',border:'1px solid rgba(220,38,38,0.2)',borderRadius:9,padding:'8px 12px',marginBottom:12}}><AlertCircle size={13}/>{error}</div>}
            {done  && <div style={{display:'flex',alignItems:'center',gap:7,fontSize:13,color:'var(--green)',background:'var(--greenLight)',border:'1px solid rgba(16,185,129,0.3)',borderRadius:9,padding:'8px 12px',marginBottom:12}}><CheckCircle2 size={13}/>PDF downloaded to your Downloads folder.</div>}
            <div style={{display:'flex',alignItems:'center',gap:12}}>
              <button onClick={generate} disabled={!allFilled||loading}
                style={{display:'inline-flex',alignItems:'center',gap:8,
                  background:allFilled&&!loading?'var(--blue)':'var(--muted)',
                  color:allFilled&&!loading?'white':'var(--dim)',
                  border:`1px solid ${allFilled&&!loading?'var(--blue)':'var(--border)'}`,
                  borderRadius:9,padding:'10px 20px',fontSize:13,fontFamily:'"Plus Jakarta Sans"',fontWeight:700,
                  cursor:allFilled&&!loading?'pointer':'not-allowed',transition:'all .2s'}}>
                {loading?<><Loader2 size={13} className="spin"/>Drafting with AI…</>:<><Download size={13}/>Generate & Download PDF</>}
              </button>
              {!allFilled&&cf.length>0&&<span style={{fontSize:12,color:'var(--dim)'}}>{cf.length-filled} fields remaining</span>}
            </div>
            <p style={{fontSize:11,color:'var(--dim)',marginTop:8}}>⚠️ AI-generated template · Verify with a qualified advocate before signing.</p>
          </div>
        )}
      </div>

      {/* Live preview */}
      <div style={{width:280,flexShrink:0,background:'var(--surface)',borderLeft:'1px solid var(--border)',display:'flex',flexDirection:'column'}}>
        <div style={{padding:'10px 16px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:7}}>
          <Eye size={13} style={{color:'var(--blue)'}}/>
          <span style={{fontSize:11,fontFamily:'"Plus Jakarta Sans"',fontWeight:700,color:'var(--sub)',textTransform:'uppercase',letterSpacing:'0.06em'}}>Live Preview</span>
        </div>
        <div style={{flex:1,overflowY:'auto',padding:16}}>
          {!sel ? (
            <div style={{height:'100%',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:10}}>
              <Scale size={24} style={{color:'var(--border)'}}/>
              <p style={{fontSize:12,color:'var(--dim)',textAlign:'center',fontFamily:'"Plus Jakarta Sans"'}}>Select a document type<br/>to see preview</p>
            </div>
          ) : (
            <div style={{background:'var(--muted)',border:'1px solid var(--border)',borderRadius:12,padding:16,fontFamily:'"Plus Jakarta Sans"'}}>
              <div style={{textAlign:'center',paddingBottom:12,marginBottom:12,borderBottom:'1px solid var(--border)'}}>
                <div style={{width:32,height:4,background:'linear-gradient(90deg,var(--blue),var(--amber))',borderRadius:9999,margin:'0 auto 10px'}}/>
                <h4 style={{fontSize:13,fontWeight:700,color:'var(--text)',marginBottom:2}}>{docTypes[sel]}</h4>
                <p style={{fontSize:10,color:'var(--dim)'}}>{new Date().toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}</p>
              </div>
              <div style={{display:'flex',flexDirection:'column',gap:8}}>
                {Object.entries(fields).filter(([,v])=>v).map(([k,v])=>(
                  <div key={k} style={{fontSize:11}}>
                    <span style={{color:'var(--blue)',fontWeight:700,display:'block',marginBottom:1,textTransform:'uppercase',letterSpacing:'0.04em',fontSize:10}}>{k.replace(/_/g,' ')}</span>
                    <span style={{color:'var(--sub)',wordBreak:'break-word'}}>{v}</span>
                  </div>
                ))}
                {!Object.values(fields).some(Boolean)&&<p style={{fontSize:11,color:'var(--dim)',textAlign:'center',padding:'8px 0'}}>Fill the form to preview</p>}
              </div>
            </div>
          )}
        </div>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}