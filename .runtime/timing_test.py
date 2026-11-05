from pathlib import Path
p=Path('tests/teacher-extension.spec.ts');s=p.read_text(encoding='utf-8')
s=s.replace("await panel.getByLabel('Session title').fill('Panel hosted class');", "await panel.getByLabel('Session title').fill('Panel hosted class');\n  await panel.getByLabel('Ask about a missed question after (seconds)').fill('0');\n  await panel.getByLabel('Time to explain the miss (seconds)').fill('60');")
s=s.replace("await student.getByLabel('Session code').fill(code);\n   await student.getByRole('button',{name:'Join class'}).click();", "const listed=student.locator('article').filter({has:student.getByRole('heading',{name:'Panel hosted class'})});\n   await expect(listed).toBeVisible();\n   await listed.getByLabel('Class code').fill(code);\n   await listed.getByRole('button',{name:'Join class'}).click();")
s=s.replace("await panel.screenshot({path:", """await panel.getByRole('button',{name:'Close question',exact:true}).click();
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
   await panel.screenshot({path:""")
p.write_text(s,encoding='utf-8')
