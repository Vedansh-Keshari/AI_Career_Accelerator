import {build} from 'esbuild';import fs from 'fs';
const css=fs.readFileSync('src/shared/theme.css','utf8');
for(const [entry,title] of [['website','AI Resume Analyzer: Guide'],['app','AI Resume Analyzer: App']]){
  const r=await build({entryPoints:['src/'+entry+'.jsx'],bundle:true,minify:true,write:false,format:'iife',jsx:'automatic',define:{'process.env.NODE_ENV':'"production"'}});
  const js=r.outputFiles[0].text.replace(/<\/script/g,'<\\/script');
  fs.writeFileSync('dist/'+entry+'.html',`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title}</title><style>${css}</style></head><body><div id="root"></div><script>${js}</script></body></html>`);
  console.log('built dist/'+entry+'.html');
}
