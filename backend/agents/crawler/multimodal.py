import os
import json
import base64
import mimetypes
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
from pypdf import PdfReader
from docx import Document
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# HELPERS
# =========================

def file_to_data_url(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def safe_read_txt(path: str, max_chars: int = 12000) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(max_chars)


def extract_pdf_text(path: str, max_chars: int = 15000) -> str:
    reader = PdfReader(path)
    chunks = []
    total = 0

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            remaining = max_chars - total
            if remaining <= 0:
                break
            piece = text[:remaining]
            chunks.append(piece)
            total += len(piece)

    return "\n".join(chunks).strip()


def extract_docx_text(path: str, max_chars: int = 15000) -> str:
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return text[:max_chars]


def sample_video_frames(
    video_path: str,
    output_dir: str,
    every_n_seconds: float = 2.0,
    max_frames: int = 8
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(int(fps * every_n_seconds), 1)

    saved = []
    idx = 0
    frame_no = 0

    while len(saved) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_no % frame_interval == 0:
            out_path = os.path.join(output_dir, f"frame_{idx:02d}.jpg")
            cv2.imwrite(out_path, frame)
            saved.append(out_path)
            idx += 1

        frame_no += 1

    cap.release()
    return saved


def extract_audio_from_video(video_path: str, output_wav: str) -> Optional[str]:
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                output_wav
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return output_wav if os.path.exists(output_wav) else None
    except Exception:
        return None


def transcribe_audio(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f,
        )
    return getattr(transcript, "text", "") or ""


# =========================
# MULTIMODAL EXTRACTORS
# =========================

def summarize_image(path: str) -> str:
    data_url = file_to_data_url(path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Describe only evidence visible in this image that could support or "
                        "contradict a reported incident. Focus on people, actions, objects, "
                        "damage, location clues, timestamps, uniforms, signs, vehicles, receipts, "
                        "chat text, and anything directly observable. Be literal."
                    )
                },
                {
                    "type": "input_image",
                    "image_url": data_url
                }
            ]
        }]
    )

    return response.output_text.strip()


def summarize_text_document(path: str) -> str:
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        extracted = extract_pdf_text(path)
    elif suffix == ".docx":
        extracted = extract_docx_text(path)
    elif suffix in {".txt", ".md", ".csv", ".json"}:
        extracted = safe_read_txt(path)
    else:
        extracted = ""

    if not extracted.strip():
        return "No extractable text found."

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are reading a document as evidence for a reported incident.

Summarize only the parts that matter for verification:
- what happened
- when
- where
- who
- what object / document / receipt / message is shown
- whether the document supports, contradicts, or is unrelated to the post

Document text:
{extracted[:12000]}
"""
    )

    return response.output_text.strip()


def summarize_video(path: str, work_dir: str = "tmp_video") -> str:
    os.makedirs(work_dir, exist_ok=True)

    frames = sample_video_frames(path, output_dir=work_dir)
    frame_summaries = []

    for frame_path in frames:
        frame_summaries.append(summarize_image(frame_path))

    transcript = ""
    audio_path = extract_audio_from_video(path, os.path.join(work_dir, "audio.wav"))
    if audio_path:
        try:
            transcript = transcribe_audio(audio_path)
        except Exception:
            transcript = ""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are combining evidence from sampled video frames and optional audio.

Frame summaries:
{json.dumps(frame_summaries, ensure_ascii=False, indent=2)}

Audio transcript:
{transcript[:6000]}

Produce one concise evidence summary describing:
- visible actions
- people / vehicles / objects
- location clues
- timing clues
- whether the video appears relevant to the incident
"""
    )

    return response.output_text.strip()


def summarize_audio(path: str) -> str:
    transcript = transcribe_audio(path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are analyzing an audio file as incident evidence.

Transcript:
{transcript[:12000]}

Summarize only evidence relevant to verification:
- what happened
- who is speaking
- time / place clues
- whether the audio supports, contradicts, or is unrelated to the post
"""
    )

    return response.output_text.strip()


def summarize_one_evidence(path: str) -> Dict[str, Any]:
    suffix = Path(path).suffix.lower()

    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    doc_exts = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    audio_exts = {".mp3", ".wav", ".m4a", ".ogg"}

    try:
        if suffix in image_exts:
            summary = summarize_image(path)
            modality = "image"
        elif suffix in doc_exts:
            summary = summarize_text_document(path)
            modality = "document"
        elif suffix in video_exts:
            summary = summarize_video(path)
            modality = "video"
        elif suffix in audio_exts:
            summary = summarize_audio(path)
            modality = "audio"
        else:
            summary = "Unsupported file type."
            modality = "unknown"

        return {
            "path": path,
            "modality": modality,
            "summary": summary
        }

    except Exception as e:
        return {
            "path": path,
            "modality": "unknown",
            "summary": f"Failed to process evidence: {str(e)}"
        }


# =========================
# FINAL VERIFIER
# =========================

def verify_post_against_evidence(post_text: str, evidence_paths: List[str]) -> Dict[str, Any]:
    evidence_items = [summarize_one_evidence(p) for p in evidence_paths]

    evidence_blob = json.dumps(evidence_items, ensure_ascii=False, indent=2)

    prompt = f"""
You are a multimodal verification agent for incident reports.

Task:
Determine whether the provided evidence supports the post.

Post:
{post_text}

Evidence summaries:
{evidence_blob}

Rules:
- "supports" = evidence materially matches the post
- "contradicts" = evidence materially conflicts with the post
- "insufficient" = related evidence exists but is too weak/incomplete
- "unrelated" = evidence does not appear relevant
- Be conservative
- Do not invent facts

Return ONLY JSON:
{{
  "support": "supports | contradicts | insufficient | unrelated",
  "confidence": 0.0,
  "reasoning": "...",
  "matched_claims": ["..."],
  "missing_claims": ["..."],
  "contradictions": ["..."]
}}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    raw = response.output_text.strip()

    try:
        result = json.loads(raw)
    except Exception:
        result = {
            "support": "insufficient",
            "confidence": 0.0,
            "reasoning": "Verifier returned invalid JSON.",
            "matched_claims": [],
            "missing_claims": [],
            "contradictions": []
        }

    result["evidence_items"] = evidence_items
    return result


# =========================
# LANGGRAPH NODE
# =========================

def multimodal_verifier_node(state: dict) -> dict:
    evidence_paths = state.get("evidence_paths") or []

    if not evidence_paths:
        state["messages"].append({
            "agent": "multimodal_verifier",
            "note": "No evidence files attached; verifier skipped."
        })
        return {
            "evidence_summary": None,
            "evidence_support": "insufficient",
            "evidence_confidence": 0.0,
            "evidence_reasoning": "No supporting files were attached.",
            "messages": state["messages"]
        }

    result = verify_post_against_evidence(
        post_text=state["raw_text"],
        evidence_paths=evidence_paths
    )

    compact_summary = [
        {
            "path": item["path"],
            "modality": item["modality"],
            "summary": item["summary"][:400]
        }
        for item in result["evidence_items"]
    ]

    state["messages"].append({
        "agent": "multimodal_verifier",
        "reasoning": "Evidence verification completed",
        "evidence_support": result["support"],
        "confidence": result["confidence"],
        "matched_claims": result.get("matched_claims", []),
        "missing_claims": result.get("missing_claims", []),
        "contradictions": result.get("contradictions", []),
        "evidence_items": compact_summary
    })

    return {
        "evidence_summary": json.dumps(compact_summary, ensure_ascii=False),
        "evidence_support": result["support"],
        "evidence_confidence": result["confidence"],
        "evidence_reasoning": result["reasoning"],
        "messages": state["messages"]
    }