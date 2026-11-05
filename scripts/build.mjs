import {spawnSync} from 'node:child_process';
// Bound native worker pools on this Windows machine; no global settings change.
const env={...process.env,RAYON_NUM_THREADS:process.env.RAYON_NUM_THREADS||'1',GOMAXPROCS:process.env.GOMAXPROCS||'2',NODE_OPTIONS:process.env.NODE_OPTIONS||'--max-old-space-size=512'};
for(const args of [['node_modules/typescript/bin/tsc','--noEmit'],['node_modules/vite/bin/vite.js','build'],['node_modules/vite/bin/vite.js','build','--config','vite.extension.config.ts'],['scripts/package-extension.mjs']]){
 const result=spawnSync(process.execPath,args,{stdio:'inherit',env,windowsHide:true});
 if(result.error){console.error(result.error.message);process.exit(1)}
 if(result.status!==0)process.exit(result.status||1);
}
