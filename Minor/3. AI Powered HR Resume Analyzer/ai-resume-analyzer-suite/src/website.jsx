import React,{useState} from "react";import {createRoot} from "react-dom/client";
import {STEPS,INFO,FAQ} from "./shared/content.js";import * as L from "./shared/logic.js";
import {useStore,Topbar,ProgressBar,Opblock,Quiz,SheetTemplates,PromptBuilder,ScoreTool} from "./shared/ui.jsx";
function Step({s,i,store,update}){
 const [try_,setTry]=useState(false);const n=s.actions.length,d=s.actions.filter((_,j)=>store.checks[s.id+":"+j]).length;
 const tgl=j=>update(x=>({...x,checks:{...x.checks,[s.id+":"+j]:!x.checks[s.id+":"+j]}}));
 return <Opblock id={s.id} cls={s.cls} badge={s.badge} title={s.title} summary={`Step ${i+1}: ${s.summary}`} done={d===n} defaultOpen={i===0}>
 <p>{s.why}</p><h4>Tasks ({d} of {n})</h4>
 {s.actions.map((a,j)=><label className="task" key={j} style={{fontWeight:400,fontSize:"1rem",margin:"6px 0"}}><input type="checkbox" checked={!!store.checks[s.id+":"+j]} onChange={()=>tgl(j)}/><span>{a}</span></label>)}
 {s.tool==="link"?<a className="btn go" style={{textDecoration:"none",display:"inline-block"}} href="app.html">Open the dashboard</a>:s.tool&&<><button className="btn" onClick={()=>setTry(!try_)}>{try_?"Cancel":"Try it out"}</button>{try_&&<div style={{marginTop:10}}>{s.tool==="sheets"&&<SheetTemplates/>}{s.tool==="prompt"&&<PromptBuilder store={store} update={update}/>}{s.tool==="score"&&<ScoreTool store={store} update={update}/>}</div>}</>}
 <Quiz key={s.id} id={s.id} q={s.quiz} store={store} update={update}/></Opblock>;
}
function App(){
 const [store,update]=useStore();
 const first=STEPS.find(s=>STEPS.indexOf(s)>=0&&s.actions.some((_,j)=>!store.checks[s.id+":"+j]));
 return <><Topbar active="website"/><div className="wrap">
 <div className="hero"><h1>Score resumes the same way, every time</h1><p>A hands-on guide to screening resumes with Google Sheets and ChatGPT or Claude. Work through six steps, try each tool right here and track your progress.</p>
 <div className="row"><a className="btn go" style={{textDecoration:"none"}} href={"#"+(first?first.id:"sheets")}>{L.doneActions(store)?"Continue where you left off":"Start step 1"}</a><a className="btn" style={{textDecoration:"none"}} href="app.html">Open the app</a></div></div>
 <ProgressBar store={store}/>
 <h2 className="sec">Overview</h2>
 <div className="cards"><div className="card"><h3>Why</h3><ul>{INFO.why.map(x=><li key={x}>{x}</li>)}</ul></div><div className="card"><h3>Who it is for</h3><ul>{INFO.who.map(x=><li key={x}>{x}</li>)}</ul></div><div className="card"><h3>Included</h3><ul>{INFO.inc.map(x=><li key={x}>{x}</li>)}</ul></div><div className="card"><h3>Not included</h3><ul>{INFO.exc.map(x=><li key={x}>{x}</li>)}</ul></div></div>
 <h2 className="sec">Guide</h2>
 {STEPS.map((s,i)=><Step key={s.id} s={s} i={i} store={store} update={update}/>)}
 {L.doneActions(store)===L.totalActions&&<div className="card"><h3>You finished the guide</h3><p>Add your candidates in the app to compare them side by side.</p><a className="btn go" style={{textDecoration:"none"}} href="app.html">Open the app</a></div>}
 <h2 className="sec">Schemas</h2>
 <details><summary>Input sheet</summary><pre className="code">{L.IN_COLS.join(" | ")}</pre></details>
 <details><summary>Output sheet</summary><pre className="code">{L.OUT_COLS.join(" | ")}</pre></details>
 <details><summary>AI reply (JSON)</summary><pre className="code">{"{\n"+L.PARAMS.map((p,i)=>`  "${p.k}": <0-${store.cfg.weights[i]}>,`).join("\n")+'\n  "summary": "<two sentences>"\n}'}</pre></details>
 <h2 className="sec">Questions</h2>{FAQ.map(f=><details key={f[0]}><summary>{f[0]}</summary><p>{f[1]}</p></details>)}
 <div className="row"><button className="btn" onClick={()=>{if(window.confirm("Reset your progress and quiz answers?"))update(s=>({...s,checks:{},quiz:{}}))}}>Reset progress</button></div>
 <footer>Progress and candidates are saved in this browser and shared with the app.</footer></div></>;
}
createRoot(document.getElementById("root")).render(<App/>);
