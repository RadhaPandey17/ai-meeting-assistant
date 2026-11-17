"""Offline test of the document input source (no Whisper / Mistral / embeddings needed).
Heavy modules are stubbed; the real doc_extractor + main.py routing are exercised.
Run: python tests/test_documents.py"""
import os, subprocess, sys, tempfile, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

calls = {}
def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m

class FakeRAG:
    def __init__(self, text, kind="meeting"): calls["rag"] = (text, kind)
    def answer_question(self, q): return "stub"
    def clear_memory(self): pass

stub("core.extractor", extract_transcript=lambda s, language="english": (calls.__setitem__("audio", s) or "audio transcript"))
stub("core.Summarize", summarize=lambda t, kind="meeting": f"summary[{kind}]", get_title=lambda t, kind="meeting": f"title[{kind}]")
stub("core.rag_engine", HybridRAG=FakeRAG)

from fastapi.testclient import TestClient
import main
c = TestClient(main.app)

def make_files(d):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from docx import Document
    cv = canvas.Canvas(str(d / "a.pdf"), pagesize=A4)
    cv.drawString(72, 780, "Invoice INV-2291 for Acme Traders, total Rs 48,500 due in 30 days.")
    cv.showPage(); cv.drawString(72, 780, "Late payment attracts 2 percent monthly interest."); cv.save()
    doc = Document(); doc.add_paragraph("Employees get 18 days of casual leave.")
    t = doc.add_table(rows=1, cols=2); t.cell(0, 0).text, t.cell(0, 1).text = "Sick leave", "12"
    doc.save(str(d / "b.docx"))
    subprocess.run(["soffice", "--headless", "--convert-to", "doc", "--outdir", str(d), str(d / "b.docx")],
                   check=True, capture_output=True)

def run():
    d = Path(tempfile.mkdtemp()); make_files(d)
    for name, needle in (("a.pdf", "[Page 2]"), ("b.docx", "Sick leave | 12"), ("b.doc", "casual leave")):
        with open(d / name, "rb") as f:
            r = c.post("/api/process/upload", files={"file": (name, f)}, data={"language": "english"})
        assert r.status_code == 200, (name, r.text)
        j = r.json()
        assert j["source_type"] == "document" and needle in j["transcript"], (name, j)
        assert j["title"] == "title[document]" and j["summary"] == "summary[document]"
        assert calls["rag"][1] == "document"
        print("upload ok:", name)

    # filesystem route + explorer flag
    r = c.post("/api/process/filesystem", json={"path": str(d / "a.pdf")}); assert r.status_code == 200
    items = c.get("/api/filesystem", params={"path": str(d)}).json()["items"]
    assert all(i["is_document"] and i["is_media"] for i in items if i["name"].endswith((".pdf", ".docx", ".doc")))

    # txt + audio keep the old "meeting" behaviour
    (d / "m.txt").write_text("hello meeting")
    j = c.post("/api/process/filesystem", json={"path": str(d / "m.txt")}).json()
    assert j["source_type"] == "audio" and calls["rag"][1] == "meeting"
    (d / "x.mp3").write_bytes(b"fake")
    j = c.post("/api/process/filesystem", json={"path": str(d / "x.mp3")}).json()
    assert j["transcript"] == "audio transcript" and j["source_type"] == "audio"

    # bad documents -> 422, not 500
    (d / "empty.pdf").write_bytes(b"not a pdf")
    r = c.post("/api/process/filesystem", json={"path": str(d / "empty.pdf")})
    assert r.status_code == 422, r.text
    (d / "blank.md").write_text("   ")
    assert c.post("/api/process/filesystem", json={"path": str(d / "blank.md")}).status_code == 422
    print("ALL OK")

def test_documents(): run()
if __name__ == "__main__": run()
