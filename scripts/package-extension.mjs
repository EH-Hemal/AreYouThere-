import fs from 'node:fs';
import archiver from 'archiver';
const manifest=JSON.parse(fs.readFileSync('extension/manifest.json','utf-8'));
if(process.env.VITE_API_ORIGIN){const origin=new URL(process.env.VITE_API_ORIGIN);if(origin.protocol!=='https:'&&!['localhost','127.0.0.1'].includes(origin.hostname))throw new Error('Release API origin must use HTTPS');manifest.host_permissions=[origin.origin+'/*']}
fs.writeFileSync('dist/extension/manifest.json',JSON.stringify(manifest,null,2));
for(const size of [16,48,128])fs.copyFileSync(`extension/icon${size}.png`,`dist/extension/icon${size}.png`);
const output=fs.createWriteStream('dist/areyouthere-extension.zip');const archive=archiver('zip',{zlib:{level:9}});archive.pipe(output);archive.directory('dist/extension',false);await archive.finalize();await new Promise((resolve,reject)=>{output.on('close',resolve);output.on('error',reject)});console.log('Extension packaged: dist/areyouthere-extension.zip');
