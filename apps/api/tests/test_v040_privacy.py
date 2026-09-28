from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_no_real_child_packet_in_fixtures() -> None:
    forbidden = (
        "handwritten observations from the real child",
        "scan of the paper packet",
        "report card pdf",
    )
    blob = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (ROOT / "apps" / "api" / "src").rglob("*.py")
    )
    lowered = blob.lower()
    for item in forbidden:
        assert item not in lowered


def test_docs_do_not_claim_alpha_equivalence() -> None:
    docs = ROOT / "docs"
    if not docs.exists():
        return
    blob = "\n".join(
        path.read_text(encoding="utf-8") for path in docs.glob("*.md")
    ).lower()
    assert "daily win is alpha at home" not in blob
    assert "proven alpha method" not in blob
    assert "2x learning" not in blob or "not" in blob
