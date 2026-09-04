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

  const DEMO_TRANSCRIPT = "Abhi payment nahi ho pa raha hai, main 15 September ko 12000 rupees pay kar dungi.";

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
      setError("Speech Recognition is not supported in this browser. Please use Chrome or use the demo transcript button.");
      return;
    }
    if (!caseDetail) return;

    setCallState("listening");
    setTranscript("");
    setInterimTranscript("");
    setVoiceResult(null);
    setError(null);

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
        setTranscript((prev) => (prev ? prev + " " + finalTranscript : finalTranscript));
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: any) => {
      setError(`Speech recognition notice: ${event.error}`);
      setCallState("idle");
    };

    recognition.onend = () => {
      setCallState("idle");
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopCall = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setCallState("idle");
  };

  const handleUseDemoTranscript = () => {
    setTranscript(DEMO_TRANSCRIPT);
    setError(null);
  };

  const processTranscript = async (textToProcess: string) => {
    if (!textToProcess.trim()) {
      setError("Please speak into the microphone or type/select a transcript first.");
      return;
    }
    setCallState("processing");
    setError(null);
    try {
      const result = await api.voicePromise(id, textToProcess.trim());
      setVoiceResult(result as VoicePromiseResponse);
      setCallState("result");

      if (result.promise_created && result.promise) {
        speak(`Payment commitment noted for ${fmtINR(result.promise.promised_amount_minor)} on ${result.promise.promised_date}. Recovery status set to WAIT.`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to process promise extraction");
      setCallState("idle");
    }
  };

  if (loadingCase) {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
        <div className="skeleton" style={{ height: 20, width: "60%", margin: "0 auto 1rem" }} />
        <div style={{ color: "var(--text-secondary)" }}>Loading recovery case details...</div>
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

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", paddingBottom: "3rem" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href={`/recovery/${id}`} style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", textDecoration: "none" }}>
          ← Back to Recovery Case
        </Link>
      </div>

      <div style={{ marginBottom: "1.75rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.35rem", letterSpacing: "-0.02em" }}>
          Hinglish Voice-Assisted Promise-to-Pay
        </h1>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
          Recover overdue revenue through a customer promise, even when the customer responds in Hinglish.
        </p>
      </div>

      {/* CASE SUMMARY CARD */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", fontWeight: 700 }}>
              Customer & Case ID
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "0.15rem" }}>
              {getCustomerDisplayName(caseDetail.customer_id)} &middot; <span style={{ fontFamily: "monospace", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{caseDetail.id}</span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.6875rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", fontWeight: 700 }}>
              Overdue / At Risk
            </div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: "0.15rem" }}>
              {fmtINR(caseDetail.amount_minor)}
            </div>
          </div>
        </div>
      </div>

      {/* 1. CUSTOMER RESPONSE */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", border: "1px solid var(--border)", borderRadius: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)" }}>
            1. Customer Response
          </div>
          <button
            onClick={handleUseDemoTranscript}
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              padding: "0.35rem 0.75rem",
              borderRadius: 6,
              border: "1px solid rgba(99,102,241,0.3)",
              background: "rgba(99,102,241,0.08)",
              color: "var(--accent)",
              cursor: "pointer",
            }}
          >
            Use demo transcript
          </button>
        </div>

        {!browserSupport?.stt && (
          <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: 6, padding: "0.625rem 0.875rem", marginBottom: "1rem", color: "#f59e0b", fontSize: "0.8125rem" }}>
            Browser speech recognition unavailable. Click <strong>"Use demo transcript"</strong> or type custom Hinglish text below.
          </div>
        )}

        {error && (
          <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 6, padding: "0.625rem 0.875rem", marginBottom: "1rem", color: "#ef4444", fontSize: "0.8125rem" }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: "1rem" }}>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Speak via microphone or click 'Use demo transcript'..."
            rows={3}
            style={{
              width: "100%",
              padding: "0.75rem",
              borderRadius: 6,
              border: "1px solid var(--border)",
              background: "var(--bg-primary)",
              color: "var(--text-primary)",
              fontSize: "0.9375rem",
              fontFamily: "inherit",
              resize: "vertical",
              outline: "none",
            }}
          />
          {interimTranscript && (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic", marginTop: "0.25rem" }}>
              {interimTranscript}
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {callState === "listening" ? (
            <button onClick={stopCall} style={{ fontSize: "0.8125rem", padding: "0.5rem 1rem", borderRadius: 6, border: "1px solid #ef4444", background: "rgba(239,68,68,0.1)", color: "#ef4444", fontWeight: 600, cursor: "pointer" }}>
              Stop Listening
            </button>
          ) : (
            <button
              onClick={startCall}
              disabled={!browserSupport?.stt}
              style={{
                fontSize: "0.8125rem",
                padding: "0.5rem 1rem",
                borderRadius: 6,
                border: "1px solid var(--border)",
                background: browserSupport?.stt ? "var(--bg-secondary)" : "rgba(255,255,255,0.05)",
                color: browserSupport?.stt ? "var(--text-primary)" : "var(--text-muted)",
                fontWeight: 600,
                cursor: browserSupport?.stt ? "pointer" : "not-allowed",
              }}
            >
              🎙️ Start Microphone
            </button>
          )}

          <button
            onClick={() => processTranscript(transcript)}
            disabled={!transcript.trim() || callState === "processing"}
            style={{
              fontSize: "0.8125rem",
              padding: "0.5rem 1.25rem",
              borderRadius: 6,
              border: "none",
              background: transcript.trim() ? "#3b82f6" : "rgba(59,130,246,0.3)",
              color: "#ffffff",
              fontWeight: 600,
              cursor: transcript.trim() ? "pointer" : "not-allowed",
            }}
          >
            {callState === "processing" ? "Extracting Promise..." : "Extract Promise"}
          </button>

          {callState === "listening" && (
            <span style={{ fontSize: "0.8125rem", color: "#ef4444", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} /> Listening for speech...
            </span>
          )}
        </div>
      </div>

      {/* 2. PROMISE DETECTED */}
      {voiceResult && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: voiceResult.promise_created ? "4px solid #10b981" : "4px solid #f59e0b", borderRadius: 8 }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: "1rem" }}>
            2. Promise Detected
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.25rem" }}>Amount</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: voiceResult.extracted.amount_minor ? "var(--text-primary)" : "#ef4444", fontFamily: "monospace" }}>
                {voiceResult.extracted.amount_minor != null ? fmtINR(voiceResult.extracted.amount_minor) : "Missing"}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.25rem" }}>Promise Date</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 600, color: voiceResult.extracted.promised_date ? "var(--text-primary)" : "#ef4444" }}>
                {voiceResult.extracted.promised_date || "Missing"}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.25rem" }}>Confidence / Status</div>
              <div style={{ fontSize: "1rem", fontWeight: 600, color: voiceResult.promise_created ? "#10b981" : "#f59e0b" }}>
                {voiceResult.promise_created ? `Captured (${(voiceResult.extracted.confidence * 100).toFixed(0)}%)` : "Incomplete / Ambiguous"}
              </div>
            </div>
          </div>

          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)", marginBottom: "0.75rem" }}>
            <strong>Source Transcript:</strong> "{voiceResult.extracted.source_text}"
          </div>

          {!voiceResult.promise_created && (
            <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: 6, padding: "0.75rem 1rem", fontSize: "0.8125rem", color: "#f59e0b" }}>
              {voiceResult.extracted.intent === "incomplete_promise" ? (
                <div>
                  <strong>Incomplete Promise:</strong> Extractor could not safely resolve both amount and date.
                  {!voiceResult.extracted.amount_minor && " Amount is missing."}
                  {!voiceResult.extracted.promised_date && " Promised date is missing."} No promise record was fabricated.
                </div>
              ) : (
                <div>
                  <strong>Ambiguous Response:</strong> No valid payment intent detected in customer statement. Requesting clarification.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 3. RECOVERY DECISION */}
      {voiceResult?.promise_created && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "4px solid #3b82f6", borderRadius: 8 }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: "1rem" }}>
            3. Recovery Decision
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.875rem", fontWeight: 800, padding: "0.35rem 0.85rem", borderRadius: 6, background: "rgba(59,130,246,0.15)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.3)", letterSpacing: "0.05em" }}>
              WAIT
            </span>
            <div style={{ fontSize: "0.875rem", color: "var(--text-primary)", fontWeight: 600 }}>
              Reason: {voiceResult.reason || "Customer has committed to a specific payment date."}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", background: "rgba(59,130,246,0.04)", padding: "0.875rem 1rem", borderRadius: 6, border: "1px solid rgba(59,130,246,0.12)", fontSize: "0.8125rem" }}>
            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem", fontWeight: 600 }}>Next Follow-up Scheduled</div>
              <div style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: "0.9375rem" }}>
                {voiceResult.follow_up_date || voiceResult.extracted.promised_date}
              </div>
            </div>
            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem", fontWeight: 600 }}>Policy Action</div>
              <div style={{ color: "var(--text-secondary)" }}>
                Immediate recovery interventions paused. No unnecessary retry or repeated contact.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. PROMISE RECORDED */}
      {voiceResult?.promise_created && (
        <div>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            4. Promise Recorded
          </div>
          <PromiseCommitment itemId={id} customerId={caseDetail.customer_id} />
        </div>
      )}
    </div>
  );
}
