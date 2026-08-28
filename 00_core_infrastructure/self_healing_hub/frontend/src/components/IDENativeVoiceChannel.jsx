import React, { useState, useRef, useEffect, useCallback } from 'react';
import RecordRTC from 'recordrtc';

const VOICE_DAEMON_PORT = (typeof window !== 'undefined' && window.__VOICE_DAEMON_PORT__) || 8765;

export default function IDENativeVoiceChannel({ onTranscriptReceived } = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Disconnected");
  const [transcript, setTranscript] = useState("");
  const [latencyMs, setLatencyMs] = useState(null);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const pingIntervalRef = useRef(null);

  // Playback incoming binary audio from daemon via Web Audio API AudioContext
  const playAudioChunk = useCallback(async (arrayBuffer) => {
    try {
      if (!audioContextRef.current) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          audioContextRef.current = new AudioCtx();
        }
      }
      const ctx = audioContextRef.current;
      if (!ctx) return;
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }
      const bufferCopy = arrayBuffer.slice(0);
      const audioBuffer = await ctx.decodeAudioData(bufferCopy);
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);
      source.start();
    } catch (e) {
      console.warn("Audio playback decode error:", e);
    }
  }, []);

  const stopVoiceMode = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (recorderRef.current) {
      recorderRef.current.stopRecording(() => {
        setIsRecording(false);
      });
      recorderRef.current = null;
    } else {
      setIsRecording(false);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: 'session_end' }));
        } catch {
          // Ignore error during shutdown
        }
        wsRef.current.close(1000, "User stopped session");
      }
      wsRef.current = null;
    }
    setStatus("Disconnected");
    setLatencyMs(null);
  }, []);

  const startVoiceMode = async () => {
    try {
      setStatus("Connecting to Voice Bridge...");
      const host = (typeof window !== 'undefined' && window.location.hostname) ? window.location.hostname : '127.0.0.1';
      const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
      const wsProtocol = isHttps ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${host}:${VOICE_DAEMON_PORT}/ws/voice`;

      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = async () => {
        try {
          setStatus("Acquiring Microphone...");
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              channelCount: 1,
              sampleRate: 16000,
              echoCancellation: true,
              noiseSuppression: true
            }
          });
          streamRef.current = stream;

          // Initialize low-latency RecordRTC with 150ms timeSlice
          recorderRef.current = new RecordRTC(stream, {
            type: 'audio',
            mimeType: 'audio/webm',
            recorderType: RecordRTC.StereoAudioRecorder,
            timeSlice: 150,
            ondataavailable: async (blob) => {
              try {
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                  const buffer = await blob.arrayBuffer();
                  wsRef.current.send(buffer);
                }
              } catch (sendErr) {
                console.error("Error transmitting audio buffer:", sendErr);
              }
            }
          });

          recorderRef.current.startRecording();
          setIsRecording(true);
          setStatus("⚡ Live Streaming (Ultravox V0.7)");

          // Dispatch initial control session handshake
          ws.send(JSON.stringify({
            type: 'session_start',
            timeSliceMs: 150,
            mimeType: 'audio/webm'
          }));

          // Heartbeat ping for RTT latency measurement
          pingIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({
                type: 'ping',
                client_time: performance.now()
              }));
            }
          }, 3000);
        } catch (micErr) {
          console.error("Failed to acquire microphone", micErr);
          setStatus("Microphone Error");
          stopVoiceMode();
        }
      };

      ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'pong' && data.client_time) {
              const rtt = Math.round(performance.now() - data.client_time);
              setLatencyMs(rtt);
            } else if (data.type === 'transcript') {
              const text = data.text || data.transcript || "";
              setTranscript(text);
              if (onTranscriptReceived) {
                onTranscriptReceived(text);
              }
            } else if (data.type === 'status') {
              setStatus(data.message || data.status || "");
            }
          } catch (jsonErr) {
            console.warn("Received non-JSON or malformed text frame:", event.data, jsonErr);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // Playback incoming binary audio frame
          playAudioChunk(event.data);
        }
      };

      ws.onerror = (err) => {
        console.error("Voice WebSocket Error:", err);
        setStatus("Voice Bridge Offline");
      };

      ws.onclose = () => {
        stopVoiceMode();
      };
    } catch (err) {
      console.error("Failed to start voice mode", err);
      setStatus("Connection / Device Error");
      stopVoiceMode();
    }
  };

  useEffect(() => {
    return () => {
      stopVoiceMode();
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [stopVoiceMode]);

  return (
    <div style={{
      padding: '16px',
      background: '#1e1e1e',
      border: '1px solid #333',
      borderRadius: '8px',
      color: '#fff',
      fontFamily: 'monospace',
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', color: '#61dafb' }}>⚡ IDE Voice Channel (Ultravox V0.7)</h3>
          {latencyMs !== null && (
            <span style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: '4px',
              background: latencyMs < 100 ? '#14532d' : latencyMs < 300 ? '#854d0e' : '#7f1d1d',
              color: latencyMs < 100 ? '#4ade80' : latencyMs < 300 ? '#fef08a' : '#fca5a5'
            }}>
              {latencyMs}ms RTT
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!isRecording ? (
            <button
              onClick={startVoiceMode}
              style={{ padding: '6px 12px', background: '#28a745', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Start Voice Code
            </button>
          ) : (
            <button
              onClick={stopVoiceMode}
              style={{ padding: '6px 12px', background: '#dc3545', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Stop Listening
            </button>
          )}
        </div>
      </div>
      <div style={{ marginTop: '12px', fontSize: '12px', color: '#aaa', display: 'flex', justifyContent: 'space-between' }}>
        <span>Status: <strong style={{ color: isRecording ? '#28a745' : '#dc3545' }}>{status}</strong></span>
        <span>MIME: audio/webm (150ms frames)</span>
      </div>
      {transcript && (
        <div style={{ marginTop: '8px', padding: '8px', background: '#000', borderRadius: '4px', fontSize: '12px', borderLeft: '3px solid #61dafb' }}>
          &gt; {transcript}
        </div>
      )}
    </div>
  );
}
