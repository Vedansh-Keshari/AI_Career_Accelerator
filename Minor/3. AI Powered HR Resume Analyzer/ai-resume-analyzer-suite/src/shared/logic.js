import {STEPS} from "./content.js";
export const PARAMS=[
{k:"analytical",n:"Analytical & Strategic",w:20,h:"problem solving, structured thinking, case work, data use, strategy roles or projects"},
{k:"initiative",n:"Initiative & Ownership",w:20,h:"things started or led, clubs, ventures, measurable outcomes"},
{k:"ai_curiosity",n:"AI & Tech Curiosity",w:20,h:"AI projects, tools used, courses, self-learning; do not penalise missing tool names"},
{k:"communication",n:"Communication",w:15,h:"blogs, newsletters, social media, speaking, anchoring, debating"},
{k:"academic",n:"Academic Merit",w:10,h:"JEE Advanced rank (better rank scores higher), CAT percentile, CGPA"},
{k:"role_alignment",n:"Role Alignment",w:15,h:"fit with the role, EdTech experience as a bonus"}];
export const IN_COLS=["Student Name","Roll No","Email","Resume Link"];
export const OUT_COLS=IN_COLS.concat(PARAMS.map(p=>p.n),["Total Score","Recommendation","Candidature Summary"]);
export const DEFAULT_CFG={role:"AI generalist leadership track at a fast-growing EdTech company",strong:80,pot:65,weights:PARAMS.map(p=>p.w),
 prefs:"Shortlist strategy leaders, not just toppers.\nDo not reject a candidate only because AI tools are not named.\nPrefer BTech or dual degrees from IITs as the strongest; other IITs and MTech are positive.\nEdTech experience is a bonus."};
export const sum=a=>a.reduce((x,y)=>x+y,0);
export const band=(t,c)=>t>=c.strong?"Strong":t>=c.pot?"Potential":"Weak";
export function buildPrompt(c){
 const crit=PARAMS.map((p,i)=>`- ${p.n} (${c.weights[i]} points): ${p.h}`).join("\n");
 const keys=PARAMS.map((p,i)=>`"${p.k}": <number from 0 to ${c.weights[i]}>`).join(", ");
 return `You are the CHRO of a fast-growing organisation. You are screening resumes for: ${c.role}.\n\nEvaluate the resume I send on these parameters. Score each one out of its maximum points:\n${crit}\n\nRules:\n${c.prefs.split("\n").filter(Boolean).map(x=>"- "+x).join("\n")}\n\nBands for the total score (out of ${sum(c.weights)}): Strong ${c.strong} or more; Potential ${c.pot} to ${c.strong-1}; Weak below ${c.pot}.\n\nReply with JSON only, no other text, in exactly this shape:\n{${keys}, "summary": "<two sentences on strengths and gaps>"}`;
}
export function scoreReply(raw,c){
 const t=raw.replace(/```json|```/g,"").trim(),a=t.indexOf("{"),b=t.lastIndexOf("}");
 if(a<0||b<a)throw new Error("No JSON found. Paste the full reply from the AI.");
 let d;try{d=JSON.parse(t.slice(a,b+1))}catch(e){throw new Error("That reply is not valid JSON. Ask the AI to reply with JSON only.")}
 const miss=[],scores=PARAMS.map((p,i)=>{const v=Number(d[p.k]);if(!isFinite(v)){miss.push(p.k);return 0}return Math.min(Math.max(v,0),c.weights[i])});
 if(miss.length)throw new Error("Missing or invalid score for: "+miss.join(", ")+".");
 const total=sum(scores);return {scores,total,rec:band(total,c),summary:String(d.summary||"")};
}
export const rowOf=x=>[x.name,x.roll,x.email,x.link,...x.scores,x.total,x.rec,x.summary].map(v=>String(v??"").replace(/[\t\r\n]+/g," "));
export const toTSV=(rows)=>rows.map(r=>r.join("\t")).join("\n");
export const toCSV=(rows)=>rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(",")).join("\n");
const PR=[["Aarav Mehta","21CS001",[.95,.9,.85,.8,.95,.9],"Led a national case competition team and shipped an AI tutoring prototype. Little formal writing."],
["Diya Nair","21EE014",[.8,.85,.9,.9,.7,.75],"Runs a popular edtech newsletter and builds with AI tools daily. Average academics."],
["Kabir Singh","21ME027",[.7,.6,.55,.5,.8,.6],"Solid analytical base with good grades. Few signs of ownership or public work."],
["Meera Iyer","21CH009",[.4,.45,.3,.5,.55,.35],"Strong coursework but no projects or leadership shown. Weak fit for the role."],
["Rohan Das","21CS033",[.85,.8,.7,.65,.85,.8],"Founded a coding club and debates at national level. AI exposure is early."]];
export function practice(c){return PR.map((p,i)=>{const scores=p[2].map((f,j)=>Math.round(f*c.weights[j]));const total=sum(scores);
 return {id:"p"+i+Date.now(),name:p[0],roll:p[1],email:p[0].split(" ")[0].toLowerCase()+"@example.com",link:"https://example.com/resume/"+p[1],scores,total,rec:band(total,c),summary:p[3]}})}
const KEY="ara.v2",mem={};
const blank=()=>({checks:{},quiz:{},cfg:DEFAULT_CFG,cands:[]});
export function load(){try{const r=localStorage.getItem(KEY);if(r)return {...blank(),...JSON.parse(r)}}catch(e){if(mem[KEY])return mem[KEY]}return mem[KEY]||blank()}
export function save(s){mem[KEY]=s;try{localStorage.setItem(KEY,JSON.stringify(s))}catch(e){}}
export const totalActions=STEPS.reduce((a,s)=>a+s.actions.length,0);
export const doneActions=s=>Object.keys(s.checks).filter(k=>s.checks[k]).length;
