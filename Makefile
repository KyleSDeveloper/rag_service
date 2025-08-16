.RECIPEPREFIX := >
.PHONY: run index evaluate eval

run:
> uvicorn rag_app.main:app --host 0.0.0.0 --port 8000 --reload

index:
> python -m rag_app.index --corpus ./corpus --out ./rag_app/index.json

# alias
eval: evaluate
evaluate:
> python -m eval.evaluate --gold ./eval/gold.jsonl --api http://localhost:8000/ask
