import {test,expect,chromium} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const credentials=JSON.parse(fs.readFileSync('.runtime/browser-test.json','utf-8'));

test('teacher hosts from the actual MV3 side panel while a student answers in the dashboard',async()=>{
 const context=await chromium.launchPersistentContext('',{channel:process.env.EXTENSION_TEST_CHANNEL||'msedge',headless:true,args:[`--disable-extensions-except=${path.resolve('dist/extension')}`,`--load-extension=${path.resolve('dist/extension')}`]});
 try{
  let [worker]=context.serviceWorkers();if(!worker)worker=await context.waitForEvent('serviceworker');
  const extensionId=worker.url().split('/')[2];expect(extensionId).toMatch(/^[a-p]{32}$/);
  const panel=await context.newPage();panel.on('pageerror',error=>console.error('Extension page error:',error.message));panel.on('crash',()=>console.error('Extension renderer crashed'));await panel.setViewportSize({width:390,height:900});await panel.goto(`chrome-extension://${extensionId}/extension/panel.html`);
  await panel.getByRole('button',{name:'Create account',exact:true}).first().click();
  await panel.getByLabel('Full name').fill('Panel Teacher');
  await panel.getByLabel('I’m joining as').selectOption('teacher');
  await panel.getByLabel('Email address').fill(credentials.newTeacher.replace('@','-extension@'));
  await panel.getByLabel('Password',{exact:true}).fill(credentials.password);
  await panel.getByRole('button',{name:'Create account',exact:true}).last().click();
  await expect(panel.getByRole('heading',{name:'Your sessions'})).toBeVisible();
  await panel.getByRole('button',{name:'Create session',exact:true}).first().click();
  await panel.getByLabel('Session title').fill('Panel hosted class');
  await panel.getByLabel('Ask about a missed question after (seconds)').fill('0');
  await panel.getByLabel('Time to explain the miss (seconds)').fill('60');
  await panel.getByRole('dialog').getByRole('button',{name:'Create session'}).click();
  await expect(panel.getByRole('heading',{name:'Panel hosted class'})).toBeVisible();
  const code=(await panel.locator('.teacher-extension-code strong').innerText()).trim();expect(code).toMatch(/^[A-Z2-9]{6}$/);

  const student=await context.newPage();await student.setViewportSize({width:1000,height:850});
  try{
   await student.goto('http://127.0.0.1:5173/');
   await student.getByRole('button',{name:'Create account',exact:true}).first().click();
   await student.getByLabel('Full name').fill('Panel Student');
   await student.getByLabel('Email address').fill(credentials.student.replace('@','-extension@'));
   await student.getByLabel('Password',{exact:true}).fill(credentials.password);
   await student.getByRole('button',{name:'Create account',exact:true}).last().click();
   const listed=student.locator('article').filter({has:student.getByRole('heading',{name:'Panel hosted class'})});
   await expect(listed).toBeVisible();
   await listed.getByLabel('Class code').fill(code);
   await listed.getByRole('button',{name:'Join class'}).click();
   await expect(student.getByRole('heading',{name:'You’re in the lobby.'})).toBeVisible();
   await expect(panel.locator('.teacher-extension-students')).toContainText('Panel Student');

   await panel.getByRole('button',{name:'Start session'}).click();
   await panel.getByRole('button',{name:'Create question'}).click();
   await panel.getByLabel('Question',{exact:true}).fill('Which structure follows FIFO?');
   for(const [index,choice] of ['Stack','Queue','Tree','Graph'].entries())await panel.getByLabel(`Choice ${String.fromCharCode(65+index)}`,{exact:true}).fill(choice);
   await panel.getByLabel('Correct answer',{exact:true}).selectOption('1');
   await panel.getByRole('button',{name:'Save question'}).click();
   await panel.getByRole('button',{name:'Send now'}).click();
   await expect(student.locator('.student-prompt')).toHaveText('Which structure follows FIFO?');
   await student.getByRole('radio').nth(1).check();
   await student.getByRole('button',{name:'Submit answer'}).click();
   await expect(student.getByRole('heading',{name:'You’re all set.'})).toBeVisible();
   await expect(panel.locator('.teacher-extension-students')).toContainText('1/1 answered');
   await panel.reload();
   await expect(panel.getByRole('heading',{name:'Panel hosted class'})).toBeVisible();
   await expect(panel.locator('.teacher-extension-students')).toContainText('1/1 answered');
   await panel.getByRole('button',{name:'Close question',exact:true}).click();
   await panel.getByRole('button',{name:'Create question',exact:true}).click();
   await panel.getByLabel('Question',{exact:true}).fill('Recovery check');
   await panel.getByLabel('Question type').selectOption('short');
   await panel.getByLabel('Time to answer (seconds)').fill('10');
   await panel.getByRole('button',{name:'Save question',exact:true}).click();
   await panel.getByRole('button',{name:'Send now',exact:true}).click();
   await expect(student.getByRole('heading',{name:'What happened?'})).toBeVisible({timeout:25000});
   await student.getByLabel('Why did you miss this question?').fill('I lost my connection briefly.');
   await student.getByRole('button',{name:'Send reason',exact:true}).click();
   await expect(panel.locator('.teacher-extension-reason')).toContainText('I lost my connection briefly.');
   await panel.screenshot({path:'verification/teacher-extension.png',fullPage:true});
  }finally{await student.close()}
 }finally{await context.close()}
});
