import React,{useState,useEffect} from "react";
import * as L from "./logic.js";
export function useStore(){
 const [s,setS]=useState(L.load());
 useEffect(()=>{const f=()=>setS(L.load());window.addEventListener("storage",f);return()=>window.removeEventListener("storage",f)},[]);
 const update=fn=>{const n=fn(L.load());L.save(n);setS(n)};
 return [s,update];
}
export function copyText(t,done){
 const ok=()=>done&&done("Copied."),fb=()=>{const a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();try{document.execCommand("copy");ok()}catch(e){done&&done("Copy failed. Select the text and copy by hand.")}document.body.removeChild(a)};
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(ok,fb);else fb();
}
export function download(name,text,type){const u=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement("a");a.href=u;a.download=name;document.body.appendChild(a);a.click();document.body.removeChild(a);setTimeout(()=>URL.revokeObjectURL(u),500)}
export function Topbar({active}){return <header className="topbar"><div className="tb-in"><span className="logo">RA</span><b className="tb-title">AI Resume Analyzer</b><nav><a className={active==="website"?"on":""} href="website.html">Guide</a><a className={active==="app"?"on":""} href="app.html">App</a></nav></div></header>}
export function ProgressBar({store}){
 const d=L.doneActions(store),t=L.totalActions,p=Math.round(d/t*100),q=Object.keys(store.quiz).filter(k=>store.quiz[k]).length;
 const lvl=p===100?"All steps done":p>=67?"Almost there":p>=34?"Halfway":p>0?"Getting started":"Not started";
 return <div className="prog" role="status"><div className="prog-row"><b>{lvl}</b><span>{d} of {t} tasks · {q} of 6 quiz answers right</span><b>{p}%</b></div><div className="bar" role="progressbar" aria-valuenow={p} aria-valuemin="0" aria-valuemax="100"><i style={{width:p+"%"}}/></div></div>;
}
export function Opblock({cls,badge,title,summary,done,defaultOpen,id,children}){
 const [open,setOpen]=useState(!!defaultOpen);
 return <div id={id} className={"op "+cls+(open?" open":"")}><button className="op-sum" onClick={()=>setOpen(!open)} aria-expanded={open}><span className="badge">{badge}</span><span className="op-path">{title}</span><span className="op-desc">{summary}</span>{done&&<span className="tick" title="Done">✓</span>}<span className="chev">{open?"▲":"▼"}</span></button>{open&&<div className="op-body">{children}</div>}</div>;
}
export function Quiz({q,id,store,update}){
 const [pick,setPick]=useState(null);const right=pick===q.a;
 return <div className="quiz"><b>Check yourself: {q.q}</b>{q.o.map((o,i)=><button key={i} className={"opt"+(pick===i?(i===q.a?" ok":" no"):"")} onClick={()=>{setPick(i);update(s=>({...s,quiz:{...s.quiz,[id]:i===q.a}}))}}>{o}</button>)}{pick!==null&&<p className={right?"good":"bad"}>{right?"Correct. ":"Not quite. "}{q.why}</p>}</div>;
}
function Msg({m}){return <span className="msg">{m}</span>}
export function SheetTemplates(){
 const [m,setM]=useState("");
 const T=({cols})=><div className="sheet"><table><thead><tr>{cols.map(c=><th key={c}>{c}</th>)}</tr></thead></table></div>;
 return <div><p className="hint">Copy a header row, then paste it into cell A1 of a new Google Sheet. It fills across the columns.</p><b>Input sheet</b><T cols={L.IN_COLS}/><button className="btn" onClick={()=>copyText(L.IN_COLS.join("\t"),setM)}>Copy input headers</button> <b className="gap">Output sheet</b><T cols={L.OUT_COLS}/><button className="btn" onClick={()=>copyText(L.OUT_COLS.join("\t"),setM)}>Copy output headers</button> <Msg m={m}/></div>;
}
export function PromptBuilder({store,update}){
 const c=store.cfg,[m,setM]=useState(""),set=p=>update(s=>({...s,cfg:{...s.cfg,...p}})),tot=L.sum(c.weights);
 return <div><label>Role you are hiring for<input value={c.role} onChange={e=>set({role:e.target.value})}/></label>
 <div className="grid">{L.PARAMS.map((p,i)=><label key={p.k}>{p.n} (points)<input type="number" min="0" max="100" value={c.weights[i]} onChange={e=>set({weights:c.weights.map((w,j)=>j===i?Math.max(0,parseInt(e.target.value,10)||0):w)})}/></label>)}</div>
 <p className={tot===100?"hint":"hint bad"}>Total points: {tot}{tot===100?"":" (should be 100)"}</p>
 <div className="grid"><label>Strong from<input type="number" value={c.strong} onChange={e=>set({strong:parseInt(e.target.value,10)||0})}/></label><label>Potential from<input type="number" value={c.pot} onChange={e=>set({pot:parseInt(e.target.value,10)||0})}/></label></div>
 <label>Rules and preferences<textarea value={c.prefs} onChange={e=>set({prefs:e.target.value})}/></label>
 <label>Your system prompt<textarea className="tall" readOnly value={L.buildPrompt(c)}/></label>
 <button className="btn go" onClick={()=>copyText(L.buildPrompt(c),setM)}>Copy prompt</button> <Msg m={m}/></div>;
}
export function ScoreTool({store,update}){
 const c=store.cfg,[f,setF]=useState({name:"",roll:"",email:"",link:""}),[json,setJson]=useState(""),[res,setRes]=useState(null),[err,setErr]=useState(""),[m,setM]=useState("");
 const run=()=>{setErr("");setM("");try{setRes(L.scoreReply(json,c))}catch(e){setRes(null);setErr(e.message)}};
 const cand=()=>({id:"c"+Date.now(),...f,...res});
 const sample=()=>{const o={};L.PARAMS.forEach((p,i)=>o[p.k]=Math.round(c.weights[i]*.75));o.summary="Strong analytical record and clear ownership. Limited public writing and no AI project yet.";setJson(JSON.stringify(o,null,2))};
 return <div><div className="grid">{[["name","Student name"],["roll","Roll no"],["email","Email"],["link","Resume link"]].map(([k,l])=><label key={k}>{l}<input value={f[k]} onChange={e=>setF({...f,[k]:e.target.value})}/></label>)}</div>
 <label>AI reply (JSON)<textarea value={json} onChange={e=>setJson(e.target.value)} placeholder='{"analytical": 15, "initiative": 12, ..., "summary": "..."}'/></label>
 <button className="btn go" onClick={run}>Execute</button> <button className="btn" onClick={sample}>Load sample reply</button>
 {err&&<p className="bad">{err}</p>}
 {res&&<div className="resp"><div className="resp-h">Response · 200</div><p className="big">{res.total} / {L.sum(c.weights)} <span className={"pill "+res.rec}>{res.rec}</span></p>
 {L.PARAMS.map((p,i)=><div className="meter" key={p.k}><span>{p.n}</span><div className="bar sm"><i style={{width:(res.scores[i]/c.weights[i]*100)+"%"}}/></div><b>{res.scores[i]}/{c.weights[i]}</b></div>)}
 <p className="hint">{res.summary}</p>
 <button className="btn go" onClick={()=>{update(s=>({...s,cands:[...s.cands,cand()]}));setM("Added to your dashboard in the App.")}}>Add to dashboard</button> <button className="btn" onClick={()=>copyText(L.rowOf({...f,...res}).join("\t"),setM)}>Copy row for Google Sheets</button> <Msg m={m}/></div>}</div>;
}
