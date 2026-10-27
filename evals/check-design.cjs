// Run with the Vite dev server on 127.0.0.1:5173; all API data is synthetic.
const fs=require('node:fs');const path=require('node:path');const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');process.chdir(root);
const tsx=path.join(root,'apps/web/ui-preview.tsx'),html=path.join(root,'apps/web/ui-preview.html');
if(fs.existsSync(tsx)||fs.existsSync(html))throw Error('Remove the existing temporary UI preview before running this check.');
try{
 fs.writeFileSync(tsx,fs.readFileSync(path.join(__dirname,'design-fixture.tsx')));
 fs.writeFileSync(html,'<html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Fieldnote synthetic UI checks</title></head><body><div id="root"></div><script type="module" src="/ui-preview.tsx"></script></body></html>');
 for(const script of ['browser-design.cjs','browser-design-states.cjs','browser-liquid-glass.cjs']){const result=spawnSync(process.execPath,[path.join(__dirname,script)],{stdio:'inherit',env:process.env});if(result.status!==0)throw Error(script+' failed');}
}finally{for(const file of [tsx,html])if(fs.existsSync(file))fs.unlinkSync(file);}
