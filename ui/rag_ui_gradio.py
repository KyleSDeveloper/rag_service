# ui/rag_ui_gradio.py
import os, requests, gradio as gr

API_URL = os.environ.get("RAG_API_URL", "http://localhost:8000/ask")
API_KEY = os.environ.get("API_KEY", "")

def ask_client(message, history, k=3):
    payload = {"question": message, "k": k}
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    answer = (data.get("answer") or "").strip()
    docs = data.get("docs") or []

    # Build nicer markdown: short answer + supporting snippets
    md = f"**Answer:** {answer or 'I couldn’t find a direct answer in your docs.'}"
    if docs:
        md += "\n\n**Sources:**\n"
        for d in docs[:3]:
            txt = (d.get("text") or "").strip().replace("\n", " ")
            if len(txt) > 400:
                txt = txt[:400] + "…"
            md += f"> {txt}\n\n— *{d.get('doc_id')}* (score={float(d.get('score',0)):.3f})\n\n"
    return md

demo = gr.ChatInterface(
    fn=ask_client,
    title="RAG Assistant",
    description="Ask a question about your corpus; answers include source snippets.",
)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)



