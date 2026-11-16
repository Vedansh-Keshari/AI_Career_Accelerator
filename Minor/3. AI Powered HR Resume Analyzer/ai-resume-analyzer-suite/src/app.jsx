import React,{useState} from "react";import {createRoot} from "react-dom/client";
import * as L from "./shared/logic.js";
import {useStore,Topbar,ProgressBar,SheetTemplates,PromptBuilder,ScoreTool,copyText,download} from "./shared/ui.jsx";
function Dashboard({store,update}){
 const c=store.cfg,[q,setQ]=useState(""),[f,setF]=useState("All"),[sort,setSort]=useState("desc"),[m,setM]=useState("");
 const all=store.cands.map(x=>({...x,rec:L.band(x.total,c)}));
 const cnt=r=>all.filter(x=>x.rec===r).length;
 const rows=all.filter(x=>(f==="All"||x.rec===f)&&(x.name+x.roll+x.email).toLowerCase().includes(q.toLowerCase())).sort((a,b)=>sort==="desc"?b.total-a.total:a.total-b.total);
 const avg=L.PARAMS.map((p,i)=>all.length?L.sum(all.map(x=>x.scores[i]))/all.length/c.weights[i]*100:0);
 const out=()=>[L.OUT_COLS,...rows.map(L.rowOf)];
 return <div>
 <div className="stats"><div className="stat"><b>{all.length}</b>Candidates</div>{["Strong","Potential","Weak"].map(r=><div key={r} className={"stat "+r}><b>{cnt(r)}</b>{r}</div>)}</div>
 {!all.length&&<div className="card" style={{marginTop:12}}><h3>No candidates yet</h3><p>Score one in the Add tab, or load five practice candidates to explore the dashboard.</p><button className="btn go" onClick={()=>update(s=>({...s,cands:L.practice(s.cfg)}))}>Load practice candidates</button></div>}
 {all.length>0&&<><h2 className="sec">Average by parameter</h2>{L.PARAMS.map((p,i)=><div className="meter" key={p.k}><span>{p.n}</span><div className="bar sm"><i style={{width:avg[i]+"%"}}/></div><b>{Math.round(avg[i])}%</b></div>)}
 <h2 className="sec">Candidates</h2>
 <div className="tools"><input placeholder="Search name, roll or email" aria-label="Search" value={q} onChange={e=>setQ(e.target.value)}/><select aria-label="Filter" value={f} onChange={e=>setF(e.target.value)}>{["All","Strong","Potential","Weak"].map(x=><option key={x}>{x}</option>)}</select><button className="btn" onClick={()=>setSort(sort==="desc"?"asc":"desc")}>Score {sort==="desc"?"high to low":"low to high"}</button></div>
 <div className="sheet"><table><thead><tr><th>Name</th><th>Roll</th><th>Total</th><th>Result</th><th>Summary</th><th></th></tr></thead><tbody>{rows.map(x=><tr key={x.id}><td>{x.name||"(no name)"}</td><td>{x.roll}</td><td><b>{x.total}</b></td><td><span className={"pill "+x.rec}>{x.rec}</span></td><td style={{whiteSpace:"normal",minWidth:240}}>{x.summary}</td><td><button className="btn" onClick={()=>update(s=>({...s,cands:s.cands.filter(y=>y.id!==x.id)}))}>Remove</button></td></tr>)}</tbody></table></div>
 {!rows.length&&<p className="hint">No candidates match.</p>}
 <div className="row"><button className="btn go" onClick={()=>download("resume-scores.csv",L.toCSV(out()),"text/csv")}>Download CSV</button><button className="btn" onClick={()=>copyText(L.toTSV(out().slice(1)),setM)}>Copy rows for Google Sheets</button><button className="btn" onClick={()=>{if(window.confirm("Remove all candidates?"))update(s=>({...s,cands:[]}))}}>Clear all</button><span className="msg">{m}</span></div></>}</div>;
}
function App(){
 const [store,update]=useStore(),[tab,setTab]=useState("dash");
 const T=[["dash","Dashboard"],["add","Add candidate"],["prompt","Prompt"],["sheets","Sheet templates"]];
 return <><Topbar active="app"/><div className="wrap"><div className="hero"><h1>Resume dashboard</h1><p>Score candidates, compare them and export the results. Your settings match the guide.</p></div>
 <ProgressBar store={store}/>
 <div className="tabs" role="tablist">{T.map(([k,l])=><button key={k} role="tab" aria-selected={tab===k} className={"tab"+(tab===k?" on":"")} onClick={()=>setTab(k)}>{l}</button>)}</div>
 {tab==="dash"&&<Dashboard store={store} update={update}/>}
 {tab==="add"&&<div className="card"><ScoreTool store={store} update={update}/></div>}
 {tab==="prompt"&&<div className="card"><PromptBuilder store={store} update={update}/></div>}
 {tab==="sheets"&&<div className="card"><SheetTemplates/></div>}
 <footer>Saved in this browser. Nothing is uploaded.</footer></div></>;
}
createRoot(document.getElementById("root")).render(<App/>);
