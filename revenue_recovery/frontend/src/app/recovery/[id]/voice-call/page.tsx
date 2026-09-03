"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail, VoicePromiseResponse } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import PromiseCommitment from "@/components/recovery/PromiseCommitment";

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

type CallState = "idle" | "listening" | "processing" | "result";

export default function VoiceCallPage() {
  const params = useParams();
  const id = params?.id as string;

  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [loadingCase, setLoadingCase] = useState(true);
  const [callState, setCallState] = useState<CallState>("idle");
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [voiceResult, setVoiceResult] = useState<VoicePromiseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [browserSupport, setBrowserSupport] = useState<{ stt: boolean; tts: boolean } | null>(null);

  const recognitionRef = useRef<any>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoadingCase(true);
    api.itemDetail(id)
      .then((detail) => setCaseDetail(detail as CaseDetail))
      .catch(() => setError("Unable to load case details"))
      .finally(() => setLoadingCase(false));
  }, [id]);

  useEffect(() => {
    const SpeechRecognition = (typeof window !== "undefined" && (window as any).SpeechRecognition) || (typeof window !== "undefined" && (window as any).webkitSpeechRecognition);
    const hasSTT = !!SpeechRecognition;
    const hasTTS = typeof window !== "undefined" && !!window.speechSynthesis;
    setBrowserSupport({ stt: hasSTT, tts: hasTTS });
    synthRef.current = typeof window !== "undefined" ? window.speechSynthesis : null;
  }, []);

  const speak = (text: string) => {
    if (!synthRef.current) return;
    synthRef.current.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.rate = 0.95;
    synthRef.current.speak(utterance);
  };

  const startCall = () => {
    if (!browserSupport?.stt) {
      setError("Speech Recognition is not supported in this browser. Please use Chrome.");
      return;
    }
    if (!caseDetail) return;

    setCallState("listening");
    setTranscript("");
    setInterimTranscript("");
    setVoiceResult(null);
    setError(null);

    const openingLine = `Namaste, aapka ${fmtINR(caseDetail.amount_minor)} ka payment pending hai. Kab clear karenge?`;
    speak(openingLine);

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      let finalTranscript = "";
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += t;
        } else {
          interim += t;
        }
      }
      if (finalTranscript) {
        setTranscript((prev) => prev + finalTranscript);
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: any) => {
      setError(`Speech recognition error: ${event.error}`);
      setCallState("idle");
    };

    recognition.onend = () => {
      setInterimTranscript("");
      if (transcript || (event as any)?.resultIndex >= 0) {
        processTranscript(transcript || (document as any)?.lastTranscript || "");
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const processTranscript = async (finalText: string) => {
    if (!finalText.trim()) {
      setError("No speech detected. Please try again.");
      setCallState("idle");
      return;
    }
    setCallState("processing");
    setTranscript(finalText);
    try {
      const result = await api.voicePromise(id, finalText);
      setVoiceResult(result as VoicePromiseResponse);
      setCallState("result");
      if (result.promise_created && result.promise) {
        speak(`Great, I have noted your promise of ${fmtINR(result.promise.promised_amount_minor)} for ${result.promise.promised_date}.`);
      } else if (result.extracted.intent === "incomplete_promise") {
        speak("I noted your response, but I need both amount and date to create a payment commitment. Please call again with full details.");
      } else {
        speak("Thank you for your response. We will follow up accordingly.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to process voice transcript");
      setCallState("idle");
    }
  };

  const stopCall = () => {
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }
    if (synthRef.current) {
      synthRef.current.cancel();
    }
    setCallState("idle");
    setInterimTranscript("");
  };

  if (loadingCase) {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
        <div className="skeleton" style={{ height: 20, width: "60%", margin: "0 auto 1rem" }} />
        <div style={{ color: "var(--text-secondary)" }}>Loading case...</div>
      </div>
    );
  }

  if (!caseDetail) {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
        <div style={{ color: "#ef4444", marginBottom: "1rem" }}>{error || "Case not found"}</div>
        <Link href="/recovery" className="btn btn-secondary">Back to Recovery</Link>
      </div>
    );
  }

  const displayTranscript = transcript + (interimTranscript ? ` ${interimTranscript}` : "");

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href={`/recovery/${id}`} style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", textDecoration: "none" }}>
          ← Back to case
        </Link>
      </div>

      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          AI Collections Call
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
          <div>
            <div className="metric-label">Customer</div>
            <div style={{ fontSize: "1rem", fontWeight: 600 }}>{getCustomerDisplayName(caseDetail.customer_id)}</div>
          </div>
          <div>
            <div className="metric-label">Amount Overdue</div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>
              {fmtINR(caseDetail.amount_minor)}
            </div>
          </div>
        </div>

        {!browserSupport?.stt && (
          <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", color: "#ef4444", fontSize: "0.8125rem" }}>
            Speech Recognition is not supported in this browser. Please use Google Chrome.
          </div>
        )}
        {browserSupport?.stt && !browserSupport?.tts && (
          <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", color: "#f59e0b", fontSize: "0.8125rem" }}>
            Text-to-speech is not available, but voice capture will work.
          </div>
        )}

        {error && (
          <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", color: "#ef4444", fontSize: "0.8125rem" }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {callState === "idle" && (
            <button onClick={startCall} className="btn btn-primary" style={{ padding: "0.625rem 1.25rem" }}>
              Start Recovery Call
            </button>
          )}
          {(callState === "listening" || callState === "processing") && (
            <button onClick={stopCall} className="btn btn-secondary" style={{ padding: "0.625rem 1.25rem" }}>
              End Call
            </button>
          )}
          {callState === "listening" && (
            <span style={{ fontSize: "0.8125rem", color: "#ef4444", fontWeight: 600 }}>
              Listening...
            </span>
          )}
          {callState === "processing" && (
            <span style={{ fontSize: "0.8125rem", color: "#3b82f6", fontWeight: 600 }}>
              Extracting promise...
            </span>
          )}
        </div>
      </div>

      {(callState === "listening" || callState === "processing" || transcript) && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            Live Transcript
          </div>
          <div style={{
            minHeight: 80,
            padding: "0.75rem 1rem",
            background: "var(--bg-primary)",
            borderRadius: 6,
            border: "1px solid var(--border)",
            fontSize: "0.9375rem",
            lineHeight: 1.6,
            color: "var(--text-secondary)",
          }}>
            {displayTranscript || (
              <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>Waiting for speech...</span>
            )}
          </div>
        </div>
      )}

      {voiceResult && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #3b82f6" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Extracted Promise
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
            <div>
              <div className="metric-label">Intent</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, fontFamily: "monospace", textTransform: "uppercase" }}>
                {voiceResult.extracted.intent.replace(/_/g, " ")}
              </div>
            </div>
            <div>
              <div className="metric-label">Amount</div>
              <div style={{ fontSize: "1rem", fontWeight: 700, fontFamily: "monospace" }}>
                {voiceResult.extracted.amount_minor != null ? fmtINR(voiceResult.extracted.amount_minor) : "—"}
              </div>
            </div>
            <div>
              <div className="metric-label">Promised Date</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                {voiceResult.extracted.promised_date || "—"}
              </div>
            </div>
          </div>

          <div style={{ marginBottom: "0.75rem" }}>
            <div className="metric-label">Confidence</div>
            <div style={{ fontSize: "0.875rem" }}>
              {voiceResult.extracted.confidence > 0
                ? `${(voiceResult.extracted.confidence * 100).toFixed(0)}%`
                : "No confidence"}
            </div>
          </div>

          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            Source: "{voiceResult.extracted.source_text}"
          </div>

          {!voiceResult.promise_created && (
            <div style={{
              background: "rgba(245,158,11,0.08)",
              border: "1px solid rgba(245,158,11,0.25)",
              borderRadius: 6,
              padding: "0.75rem 1rem",
              fontSize: "0.8125rem",
              color: "#f59e0b",
            }}>
              {voiceResult.extracted.intent === "incomplete_promise"
                ? "Promise is incomplete — missing amount or date. No payment commitment was created."
                : voiceResult.extracted.intent === "ambiguous"
                  ? "Transcript was ambiguous — no valid payment intent detected. No commitment was created."
                  : "No valid promise could be created from this transcript."}
            </div>
          )}
        </div>
      )}

      {voiceResult?.promise_created && voiceResult.promise && (
        <PromiseCommitment itemId={id} customerId={caseDetail.customer_id} />
      )}
    </div>
  );
}
