/** Optional automated recorder. Use only in an explicitly authorized test browser. */
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.argv[3] || 'playwright');

(async () => {
  const url = process.argv[2];
  if (!url || new URL(url).hostname !== '127.0.0.1') throw new Error('Pass the loopback URL printed by make_demo_receiver.py');
  const folder = path.resolve(__dirname, '../.agent/recording');
  fs.mkdirSync(folder,{recursive:true});
  const browser = await chromium.launch({channel:'msedge',headless:true,args:['--disable-background-timer-throttling']});
  const context = await browser.newContext({viewport:{width:1600,height:1080},deviceScaleFactor:1});
  const page = await context.newPage();
  const errors=[],consoleMessages=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error') consoleMessages.push({text:message.text(),url:message.location().url});});
  try {
    await page.goto(url,{waitUntil:'networkidle',timeout:30000});
    await page.screenshot({path:path.join(folder,'recording-start.png'),fullPage:true});
    console.log('Recording page started');
    await page.waitForFunction(()=>['complete','failed'].includes(document.documentElement.dataset.recording),{},{timeout:100000});
    await page.screenshot({path:path.join(folder,'recording-finish.png'),fullPage:true});
    const state=await page.evaluate(()=>({state:document.documentElement.dataset.recording,status:document.getElementById('demo-recording-status')?.textContent}));
    fs.writeFileSync(path.join(folder,'browser-validation.json'),JSON.stringify({state,errors,consoleMessages},null,2));
    console.log(JSON.stringify({state,errors,consoleMessages}));
    if (state.state!=='complete' || errors.length) process.exitCode=1;
  } finally {
    await context.close();await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
