import json, re
from scipy.stats import beta
R="/tmp/claude-0/-home-claude/e769ad94-37b0-5fe5-970c-4fda8e3cbadc/scratchpad/medkarta-security-eval/results/replication_results.json"
d=json.load(open(R))
def cp(k,n,a=0.05):
    lo=0.0 if k==0 else beta.ppf(a/2,k,n-k+1)
    hi=1.0 if k==n else beta.ppf(1-a/2,k+1,n-k)
    return lo*100,hi*100
DET=["D1","D2","D3","D4","D5","D6","D7","D8"]
TARGET=lambda name: "D"+re.search(r"F(\d)",name.split("/")[1]).group(1) if re.search(r"F(\d)",name.split("/")[1]) else ("D4" if "FAULT_D4" in name else None)
rows=[]
tp=fn=fp=tn=0; per={}
excluded_sat=0
for key,v in d.items():
    proj,st=key.split("/")
    if st in("BASE","REPAIR"): continue
    t=TARGET(key); base=d[proj+"/BASE"]
    p=per.setdefault(proj,[0,0,0,0,0])
    for det in DET:
        b=base[det][0]; s=v[det][0]
        if b!="PASS" or s not in("PASS","FAIL"):
            if b=="FAIL" and s in("PASS","FAIL"): excluded_sat+=1
            continue
        trig = s=="FAIL"
        if det==t:
            if trig: p[0]+=1
            else: p[1]+=1
        else:
            if trig: p[2]+=1
            else: p[3]+=1
    if base[t][0]=="FAIL": p[4]+=1   # uninformative fault (already FAIL in BASE)
for proj,p in per.items(): print(proj,"TP",p[0],"FN",p[1],"FP",p[2],"TN",p[3],"uninformative",p[4])
TP=sum(p[0] for p in per.values()); FN=sum(p[1] for p in per.values()); FP=sum(p[2] for p in per.values()); TN=sum(p[3] for p in per.values())
print("replication TP",TP,"FN",FN,"FP",FP,"TN",TN,"saturated cells excluded",excluded_sat)
# ShifoSafe: 8 faults x 8 detectors, diagonal
S_TP,S_FN,S_FP,S_TN=8,0,0,56
for name,(a,b,c,e) in {"ShifoSafe":(S_TP,S_FN,S_FP,S_TN),"Replication":(TP,FN,FP,TN),"Total":(S_TP+TP,S_FN+FN,S_FP+FP,S_TN+TN)}.items():
    n1=a+b; n2=c+e
    r=cp(a,n1); f=cp(c,n2)
    print(f"{name}: detection {a}/{n1} = {100*a/n1:.1f}% CI [{r[0]:.1f},{r[1]:.1f}]; false alarms {c}/{n2} = {100*c/n2:.1f}% CI [{f[0]:.1f},{f[1]:.1f}]")
for lab,(k,n) in {"ZAP 1/8":(1,8),"Bandit/Semgrep 0/16":(0,16),"pentest detectors 0/9":(0,9),"in-scope 0/1":(0,1)}.items():
    lo,hi=cp(k,n); print(lab,f"{100*k/n:.1f}% [{lo:.1f},{hi:.1f}]")
