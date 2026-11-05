const assert=require('node:assert/strict');const fs=require('node:fs');
let callback, active=false, completions=0, ticks=[];
const source=fs.readFileSync('frontend/src/countdown.js','utf8').replace('export function','function');
const start=new Function('setInterval','clearInterval',source+'; return startCountdown;')((fn,delay)=>{assert.equal(delay,1000);callback=fn;active=true;return 1;},()=>{active=false;});
const cancel=start(5,n=>ticks.push(n),()=>completions++);
for(let i=0;i<4;i++) {if(active)callback();}
assert.equal(completions,0);assert.deepEqual(ticks,[5,4,3,2,1]);
if(active)callback();assert.equal(completions,1);assert.equal(active,false);
const cancelSecond=start(5,()=>{},()=>completions++);cancelSecond();if(active)callback();assert.equal(completions,1);
console.log('Sirine: countdown 5 detik, sekali kirim, dan pembatalan lolos.');
