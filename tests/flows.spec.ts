import {test,expect,chromium} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
const credentials=JSON.parse(fs.readFileSync('.runtime/browser-test.json','utf-8'));
test('actual MV3 extension and teacher dashboard: join, answer, reconnect, schedule, review, export',async({browser})=>{
 const context=await chromium.launchPersistentContext('',{channel:process.env.EXTENSION_TEST_CHANNEL||'msedge',headless:true,args:[`--disable-extensions-except=${path.resolve('dist/extension')}`,`--load-extension=${path.resolve('dist/extension')}`]});
 let scheduler:ReturnType<typeof spawn>|undefined;
 try{
  let [worker]=context.serviceWorkers();if(!worker)worker=await context.waitForEvent('serviceworker');
  const extensionId=worker.url().split('/')[2];expect(extensionId).toMatch(/^[a-p]{32}$/);
  const permissions=await worker.evaluate(()=>chrome.permissions.getAll());
  expect(permissions.permissions).not.toContain('history');expect(permissions.permissions).not.toContain('tabs');
  const panel=await context.newPage();panel.setDefaultTimeout(10000);await panel.setViewportSize({width:390,height:900});await panel.goto(`chrome-extension://${extensionId}/extension/panel.html`);
  await panel.getByRole('button',{name:'Create account',exact:true}).click();
  await panel.getByLabel('Full name').fill('QA Student');await panel.getByLabel('Email address').fill(credentials.student);await panel.getByLabel('Password',{exact:true}).fill(credentials.password);await panel.getByRole('button',{name:'Create account',exact:true}).last().click();
  await expect(panel.getByRole('heading',{name:'Your seat is ready.'})).toBeVisible();
  const teacherContext=await browser.newContext({viewport:{width:1440,height:1000}});const teacher=await teacherContext.newPage();teacher.on('pageerror',error=>console.error('Teacher page error:',error.message));teacher.on('crash',()=>console.error('Teacher renderer crashed'));await teacher.goto('/');
  await teacher.getByLabel('Email address').fill(credentials.teacher);await teacher.getByLabel('Password',{exact:true}).fill(credentials.password);await teacher.getByRole('button',{name:'Sign in',exact:true}).last().click();
  await expect(teacher.getByRole('heading',{name:'Hello, QA.'})).toBeVisible();
  fs.mkdirSync('verification',{recursive:true});await teacher.screenshot({path:'verification/teacher-overview.png',fullPage:true});
  await teacher.getByRole('button',{name:'Create session',exact:true}).click();await teacher.getByLabel('Session title').fill('QA · Data structures studio');await teacher.getByLabel('Course or group (optional)').fill('CSE 2201');await teacher.getByRole('dialog').getByRole('button',{name:'Create session'}).click();
  await expect(teacher.getByRole('heading',{name:'QA · Data structures studio'})).toBeVisible();
  const code=(await teacher.locator('.code-copy strong').innerText()).trim();await panel.getByLabel('Session code').fill(code);await panel.getByRole('button',{name:'Join class'}).click();await expect(panel.getByRole('heading',{name:'You’re in the lobby.'})).toBeVisible();
  await expect(teacher.locator('tbody')).toContainText('QA Student');
  await teacher.getByRole('button',{name:'Start session',exact:true}).click();
  await teacher.getByRole('button',{name:'Create question',exact:true}).click();await teacher.getByLabel('Question',{exact:true}).fill('Which structure follows FIFO?');
  for(const [i,value] of ['Stack','Queue','Tree','Graph'].entries())await teacher.getByLabel(`Choice ${String.fromCharCode(65+i)}`,{exact:true}).fill(value);
  await teacher.getByLabel('Correct answer',{exact:true}).selectOption('1');await teacher.getByRole('button',{name:'Save question',exact:true}).click();await teacher.getByRole('button',{name:'Send now',exact:true}).click();
  await expect(panel.locator('.student-prompt')).toBeVisible();await expect(teacher.getByText('Live updates connected',{exact:true})).toBeVisible();
  await worker.evaluate(()=>chrome.storage.local.set({verificationPing:Date.now()}));
  await expect.poll(()=>worker.evaluate(()=>chrome.action.getBadgeText({}))).toBe('1');
  await panel.getByRole('radio').nth(1).check();await panel.getByRole('button',{name:'Submit answer',exact:true}).click();await expect(panel.getByRole('heading',{name:'You’re all set.'})).toBeVisible();
  await expect(teacher.locator('tbody').getByText('answered',{exact:true})).toBeVisible();await panel.reload();await expect(panel.getByRole('heading',{name:'You’re all set.'})).toBeVisible();
  await expect.poll(()=>worker.evaluate(()=>chrome.action.getBadgeText({}))).toBe('');
  await panel.screenshot({path:'verification/student-extension.png',fullPage:true});await teacher.screenshot({path:'verification/teacher-live.png',fullPage:true});
  await context.setOffline(true);await expect(panel.getByText(/Reconnecting to live updates/)).toBeVisible();await context.setOffline(false);await expect(panel.getByRole('heading',{name:'You’re all set.'})).toBeVisible();
  await teacher.getByRole('button',{name:'Close question',exact:true}).click();
  const token=await teacher.evaluate(()=>sessionStorage.getItem('ayt-token'));const sid=new URL(teacher.url()).searchParams.get('session');
  const request=teacherContext.request;const headers={Authorization:`Token ${token}`};
  const scheduled=await request.post(`http://127.0.0.1:8000/api/sessions/${sid}/questions/`,{headers,data:{prompt:'In one word, how is the pace?',kind:'short',duration:10,scheduled_at:new Date(Date.now()+2000).toISOString()}});expect(scheduled.status()).toBe(201);
  // The worker starts after the due time: delivery must recover from MySQL.
  await expect.poll(()=>Date.now(),{timeout:5000}).toBeGreaterThan(Date.now()+2100);
  scheduler=spawn(path.resolve('.venv/Scripts/python.exe'),['backend/manage.py','run_scheduler'],{env:{...process.env,MYSQL_DATABASE:'test_areyouthere'},windowsHide:true});
  await expect(panel.locator('.student-prompt')).toBeVisible();
  await expect(panel.getByRole('button',{name:'Explain this miss',exact:true})).toBeVisible({timeout:25000});await panel.getByRole('button',{name:'Explain this miss',exact:true}).click();await panel.getByLabel('What happened?').fill('My connection briefly dropped.');await panel.getByRole('button',{name:'Send reason',exact:true}).click();
  await teacher.getByRole('button',{name:/Reason review/}).click();await expect(teacher.getByText('My connection briefly dropped.',{exact:true})).toBeVisible();await teacher.getByLabel('Optional review note').fill('Thanks for letting me know.');await teacher.getByRole('button',{name:'Save review',exact:true}).click();await expect(panel.getByText('excused',{exact:true})).toBeVisible();
  const downloadPromise=teacher.waitForEvent('download');await teacher.getByRole('button',{name:'Export report',exact:true}).click();const download=await downloadPromise;expect(download.suggestedFilename()).toContain('areyouthere-session-');
  await teacher.getByRole('button',{name:'End session',exact:true}).click();await teacher.getByRole('dialog').getByRole('button',{name:'End session',exact:true}).click();await expect(panel.getByRole('heading',{name:'That’s a wrap.'})).toBeVisible();
  await teacher.setViewportSize({width:390,height:844});await teacher.screenshot({path:'verification/teacher-mobile.png',fullPage:true,animations:'disabled'});
  const overflow=await teacher.evaluate(()=>document.documentElement.scrollWidth>innerWidth);expect(overflow).toBe(false);
  await teacherContext.close();
 }finally{scheduler?.kill();await context.close()}
});

test('new teacher can register, create and start a session without approval',async({browser})=>{
 const context=await browser.newContext();const teacher=await context.newPage();
 try{
  await teacher.goto('http://127.0.0.1:5173/');await teacher.getByRole('button',{name:'Create account',exact:true}).click();await teacher.getByLabel('Full name').fill('QA New Teacher');await teacher.getByRole('combobox').selectOption('teacher');await teacher.getByLabel('Email address').fill(credentials.newTeacher);await teacher.getByLabel('Password',{exact:true}).fill(credentials.password);await teacher.getByRole('button',{name:'Create account',exact:true}).last().click();
  await expect(teacher.getByRole('button',{name:'Create session',exact:true})).toBeVisible();
  await expect(teacher.getByText('Your classroom is almost ready.',{exact:true})).toHaveCount(0);
  await expect(teacher.getByRole('button',{name:'Teacher approvals',exact:true})).toHaveCount(0);
  await teacher.getByRole('button',{name:'Create session',exact:true}).click();await teacher.getByLabel('Session title').fill('QA · Ready from registration');await teacher.getByRole('dialog').getByRole('button',{name:'Create session',exact:true}).click();
  await expect(teacher.getByRole('heading',{name:'QA · Ready from registration',exact:true})).toBeVisible();await teacher.getByRole('button',{name:'Start session',exact:true}).click();await expect(teacher.locator('.heading-meta').getByText('live',{exact:true})).toBeVisible();await expect(teacher.getByText('Live updates connected',{exact:true})).toBeVisible();
 }finally{await context.close()}
});

