import argparse, json, random
from pathlib import Path
PROMPTS=["What is the deductible?","Explain coinsurance in one sentence.",
         "How do I add a dependent?","Define the out-of-pocket maximum."]
def main():
  ap=argparse.ArgumentParser(); ap.add_argument("--out",required=True); ap.add_argument("--n",type=int,default=50)
  a=ap.parse_args(); Path(a.out).parent.mkdir(parents=True,exist_ok=True)
  with open(a.out,"w",encoding="utf-8") as f:
    for i in range(a.n):
      f.write(json.dumps({"id":i+1,"question":random.choice(PROMPTS),"answer":""})+"\n")
  print(f"Wrote {a.n} Q templates to {a.out}. Fill the answers.")
if __name__=="__main__": main()
