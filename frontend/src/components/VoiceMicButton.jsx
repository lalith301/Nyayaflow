import { useState, useCallback } from 'react'
import { Mic, MicOff, Loader2 } from 'lucide-react'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { transcribeAudio } from '../api'
import { T } from '../App'

export default function VoiceMicButton({ onTranscribed, disabled }) {
  const [status, setStatus] = useState('idle')

  const onComplete = useCallback(async (blob, ext) => {
    setStatus('transcribing')
    try {
      const r = await transcribeAudio(blob, ext)
      if (r.text) { onTranscribed(r.text); setStatus('idle') }
      else { setStatus('error'); setTimeout(()=>setStatus('idle'),2500) }
    } catch { setStatus('error'); setTimeout(()=>setStatus('idle'),2500) }
  }, [onTranscribed])

  const { isRecording, startRecording, stopRecording } = useVoiceRecorder(onComplete)

  const click = () => {
    if (disabled) return
    if (isRecording) { stopRecording(); setStatus('transcribing') }
    else { setStatus('recording'); startRecording() }
  }

  return (
    <div style={{ position:'relative' }}>
      <button onClick={click} disabled={disabled||status==='transcribing'} title="Voice input" style={{
        width:44, height:44, borderRadius:11, display:'flex', alignItems:'center', justifyContent:'center',
        background: isRecording ? '#FEE2E2' : 'var(--muted)',
        color: isRecording ? '#DC2626' : status==='transcribing' ? 'var(--amber)' : 'var(--dim)',
        border:`1px solid ${isRecording ? '#FECACA' : 'var(--border)'}`,
        cursor:'pointer', transition:'all .15s', flexShrink:0,
      }}>
        {status==='transcribing'?<Loader2 size={16} className="spin"/>:isRecording?<MicOff size={16}/>:<Mic size={16}/>}
      </button>
      {(isRecording||status==='transcribing') && (
        <div style={{ position:'absolute',bottom:'calc(100% + 8px)',left:'50%',transform:'translateX(-50%)',background:'var(--text)',color:'white',borderRadius:7,padding:'4px 10px',fontSize:11,whiteSpace:'nowrap',fontFamily:'"Plus Jakarta Sans"',fontWeight:500,boxShadow:'0 4px 12px rgba(0,0,0,0.15)' }}>
          {isRecording ? '● Recording…' : '⏳ Transcribing…'}
        </div>
      )}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}