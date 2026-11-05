// Read-only account access; a temporary heading string checks responsive wrapping.
import fs from 'node:fs';
import {chromium} from 'playwright';
const text=fs.readFileSync('.runtime/admin-login.txt','utf-8');
const email=text.match(/Email: (.+)/)[1],password=text.match(/Password: (.+)/)[1];
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const page=await browser.newPage({viewport:{width:390,height:844}});await page.goto('http://127.0.0.1:5173/');
 await page.getByLabel('Email address').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).last().click();await page.locator('.page-heading h1').waitFor();
 console.log(await page.locator('.page-heading h1').evaluate(el=>{el.textContent='QA · Data structures studio';const s=getComputedStyle(el),r=el.getBoundingClientRect();return {width:r.width,right:r.right,scrollWidth:el.scrollWidth,whiteSpace:s.whiteSpace,font:s.fontFamily,display:s.display,parentWidth:el.parentElement.getBoundingClientRect().width,text:el.textContent}}));
}finally{await browser.close()}
