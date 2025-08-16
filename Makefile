.RECIPEPREFIX := >
.PHONY: run index evaluate eval

run:
> uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

index:
> python -m app.index --corpus ./corpus --out ./app/index.json

# alias
eval: evaluate
evaluate:
> python -m eval.evaluate --gold ./eval/gold.jsonl --api http://localhost:8000/ask
