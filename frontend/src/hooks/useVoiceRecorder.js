import { useState, useRef, useCallback } from 'react'

/**
 * useVoiceRecorder
 * Manages microphone access and MediaRecorder lifecycle.
 * Returns { isRecording, startRecording, stopRecording, error }
 */
export function useVoiceRecorder(onRecordingComplete) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError]             = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef        = useRef([])

  const startRecording = useCallback(async () => {
    setError(null)
    chunksRef.current = []

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Prefer webm/opus; fall back to whatever the browser supports
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/ogg'

      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        const ext  = mimeType.includes('webm') ? 'webm' : 'ogg'
        onRecordingComplete(blob, ext)
        // Release mic
        stream.getTracks().forEach(t => t.stop())
        setIsRecording(false)
      }

      recorder.start(250)  // collect chunks every 250ms
      setIsRecording(true)
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone access and try again.')
      } else {
        setError(`Could not start recording: ${err.message}`)
      }
      setIsRecording(false)
    }
  }, [onRecordingComplete])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  return { isRecording, startRecording, stopRecording, error }
}
