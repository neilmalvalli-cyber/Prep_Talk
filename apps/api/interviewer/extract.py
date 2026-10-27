"""Bounded PDF worker; document parsing never runs in the API process."""
import io
import json
import sys


def main():
    if sys.platform != "win32":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF support is unavailable on the API server. Sync API dependencies, restart, or paste resume text.") from exc
    raw = sys.stdin.buffer.read(10*1024*1024+1)
    if len(raw) > 10*1024*1024:
        raise ValueError("Resume exceeds 10 MiB. Upload a smaller file or paste text.")
    reader = PdfReader(io.BytesIO(raw), strict=False)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are unsupported. Export an unencrypted text PDF or paste text.")
    if len(reader.pages) > 20:
        raise ValueError("PDF exceeds 20 pages. Upload a shorter resume.")
    pages = []
    count = 0
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        count += len(text)
        if count > 50000:
            raise ValueError("Extracted text exceeds 50,000 characters. Shorten the resume.")
        pages.append({"page": i+1, "text": text})
    if not any(p["text"].strip() for p in pages):
        raise ValueError("No readable text found. Image-only PDFs need pasted text or a text-based PDF.")
    print(json.dumps({"pages": pages}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, ValueError) else "PDF exceeded parser memory limits. Upload a smaller PDF or paste text." if isinstance(exc, MemoryError) else "Malformed PDF. Export a new PDF or paste text."}))
        sys.exit(1)
