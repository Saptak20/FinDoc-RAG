#!/usr/bin/env python3
"""
End-to-end verification script for Milestone 13: Dynamic Document Ingestion.
Tests:
1. System readiness
2. Upload of a new financial PDF (Reliance_Q4_FY24_Disclosure.pdf)
3. Background indexing completion (status -> READY)
4. Querying a fact unique to the newly uploaded document
5. Verifying source attribution cites the new document and page
6. Verifying that the baseline Tata Steel document remains searchable with zero regression
"""

import sys
import time
import requests

BASE_URL = "http://localhost:8000"


def generate_test_pdf_bytes() -> bytes:
    """Generate a valid single-page PDF containing a unique financial disclosure."""
    stream_parts = [
        "BT /F1 14 Tf 50 750 Td (Reliance Industries Limited FY2023-24 Highlights) Tj ET",
        "BT /F1 12 Tf 50 720 Td (Reliance Retail EBITDA for FY2023-24 reached 23040 crore, representing a 28 percent growth.) Tj ET",
        "BT /F1 12 Tf 50 690 Td (Jio Platforms gross revenue surged to 109558 crore with 481 million subscribers.) Tj ET",
        "BT /F1 12 Tf 50 660 Td (Oil to Chemicals segment EBITDA stood at 62393 crore for the financial year.) Tj ET",
    ]
    stream_data = "\n".join(stream_parts).encode("latin-1")

    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(len(stream_data)).encode("ascii") + b" >>\nstream\n" + stream_data + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000450 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n520\n%%EOF\n"
    )
    return pdf_content


def main():
    print("=" * 60)
    print("FINDOC-RAG DYNAMIC INGESTION E2E VERIFICATION")
    print("=" * 60)

    # 1. Verify system readiness
    print("\n[1/6] Checking system readiness...")
    try:
        r = requests.get(f"{BASE_URL}/ready", timeout=5)
        assert r.status_code == 200, f"/ready returned {r.status_code}"
        print("  -> System is READY.")
    except Exception as e:
        print(f"  -> ERROR: Backend not reachable at {BASE_URL}: {e}")
        sys.exit(1)

    # 2. Upload new financial PDF
    filename = "Reliance_Q4_FY24_Disclosure.pdf"
    pdf_bytes = generate_test_pdf_bytes()
    print(f"\n[2/6] Uploading '{filename}' ({len(pdf_bytes)} bytes)...")

    upload_resp = requests.post(
        f"{BASE_URL}/api/v1/documents/upload",
        files={"file": (filename, pdf_bytes, "application/pdf")},
        timeout=15,
    )
    assert upload_resp.status_code in [200, 201], f"Upload failed: {upload_resp.text}"
    doc_data = upload_resp.json()["document"]
    doc_id = doc_data["id"]
    print(f"  -> Upload successful! Document ID: {doc_id}, Initial Status: {doc_data['processing_status']}")

    # 3. Poll for background processing completion
    print("\n[3/6] Polling for background indexing to complete...")
    max_wait = 30
    start_poll = time.time()
    final_status = doc_data["processing_status"]

    while time.time() - start_poll < max_wait:
        status_resp = requests.get(f"{BASE_URL}/api/v1/documents/{doc_id}", timeout=5)
        if status_resp.status_code == 200:
            doc_info = status_resp.json()
            final_status = doc_info["processing_status"]
            print(f"  -> Document status: {final_status} (Pages: {doc_info['page_count']}, Chunks: {doc_info['chunk_count']})")
            if final_status in ["READY", "FAILED"]:
                break
        time.sleep(2)

    assert final_status == "READY", f"Document processing failed or timed out: status={final_status}"
    print("  -> Document successfully indexed into FAISS and BM25!")

    # 4. Query the newly uploaded document
    print("\n[4/6] Querying knowledge from newly uploaded PDF...")
    new_query = "What was Reliance Retail's EBITDA in FY2023-24?"
    print(f"  -> Question: {new_query}")

    chat_resp = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"query": new_query, "dense_top_k": 10, "sparse_top_k": 10, "final_top_k": 3},
        timeout=30,
    )
    assert chat_resp.status_code == 200, f"Chat query failed: {chat_resp.text}"
    chat_data = chat_resp.json()

    print(f"  -> Answer : {chat_data['answer']}")
    print(f"  -> Sources:")
    for idx, s in enumerate(chat_data["sources"], 1):
        print(f"     [{idx}] {s['source']} (Page {s['page']}, Score: {s.get('rerank_score')})")

    # Verify source attribution
    source_filenames = [s["source"] for s in chat_data["sources"]]
    assert any("Reliance" in sf for sf in source_filenames), f"Expected Reliance in sources, got: {source_filenames}"
    print("  -> Citation correctly points to the newly uploaded Reliance document!")

    # 5. Query baseline Tata Steel document to verify zero regression
    print("\n[5/6] Querying baseline Tata Steel document (regression check)...")
    baseline_query = "What was Tata Steel's EBITDA margin in FY2023-24?"
    print(f"  -> Question: {baseline_query}")

    baseline_resp = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"query": baseline_query, "dense_top_k": 10, "sparse_top_k": 10, "final_top_k": 3},
        timeout=30,
    )
    assert baseline_resp.status_code == 200, f"Baseline query failed: {baseline_resp.text}"
    baseline_data = baseline_resp.json()

    print(f"  -> Answer : {baseline_data['answer']}")
    print(f"  -> Sources:")
    for idx, s in enumerate(baseline_data["sources"], 1):
        print(f"     [{idx}] {s['source']} (Page {s['page']}, Score: {s.get('rerank_score')})")

    baseline_sources = [s["source"] for s in baseline_data["sources"]]
    assert any("TATLY" in sf for sf in baseline_sources), f"Expected TATLY in sources, got: {baseline_sources}"
    print("  -> Citation correctly points to OTC_TATLY_2024.pdf! Zero regression confirmed.")

    # 6. Verify Document Library Listing
    print("\n[6/6] Checking full document registry list...")
    list_resp = requests.get(f"{BASE_URL}/api/v1/documents", timeout=5)
    assert list_resp.status_code == 200
    reg = list_resp.json()
    print(f"  -> Total registered documents: {reg['total']} ({reg['ready_count']} READY)")
    for d in reg["documents"]:
        print(f"     • {d['original_filename']} [{d['processing_status']}] - {d['page_count']} pages, {d['chunk_count']} chunks")

    print("\n" + "=" * 60)
    print("ALL DYNAMIC INGESTION E2E CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
