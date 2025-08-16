.RECIPEPREFIX := >
.PHONY: run index evaluate

run:
> API_KEY=$(API_KEY) RATE_LIMIT_PER_MIN=$(RATE_LIMIT_PER_MIN) \
  python -m uvicorn rag_app.main:app --host 0.0.0.0 --port 8010

index:
> python -m rag_app.index --corpus ./corpus --out ./rag_app/index.json

evaluate:
> python -m eval.evaluate --gold ./eval/gold.jsonl --api http://localhost:8010/ask --k 5

