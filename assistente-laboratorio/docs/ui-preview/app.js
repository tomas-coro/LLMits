(() => {
  'use strict';
  const conf = window.LAB_ASSISTANT_CONFIG || {};
  const isApi = Boolean(typeof conf.endpoint === 'string' && conf.endpoint.trim());
  const $ = (id) => document.getElementById(id);
  const state = { selected: 'automatico', expanded: false, view: 'home', messages: [], pending: false, controller: null, toastTimer: null };

  // Tutte le capacità sono dati: per aggiungere un nuovo tool basta aggiungere un oggetto.
  // "available" descrive capacità dell'app originale; questa distribuzione è un'anteprima separata.
  const capabilities = [
    { id:'automatico', title:'Automatico', subtitle:'L’assistente decide', kind:'core', status:'Principale', description:'Fai una domanda senza scegliere uno strumento. Il modello deciderà autonomamente come rispondere.', examples:['Che ore sono a Tokyo?','Quanti km sono 5000 m?'] },
    { id:'ora', title:'Ora', subtitle:'Città e fusi orari', kind:'core', description:'Domande sull’ora in una città e sulle differenze tra fusi orari.', examples:['Che ore sono a Tokyo?','Che ora è a New York?'], showcase:{q:'Che ore sono a Tokyo?',a:()=>'A Tokyo sono le '+new Intl.DateTimeFormat('it-IT',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit'}).format(new Date())+'.'} },
    { id:'conversioni', title:'Conversioni', subtitle:'Misure e temperature', kind:'core', description:'Conversioni fra lunghezze, distanze e temperature espresse in modo naturale.', examples:['Quanti km sono 5000 m?','Converti 25 °C in °F'], showcase:{q:'Quanti km sono 5000 m?',a:()=>'5000 metri sono 5 km.'} },
    { id:'meteo', title:'Meteo', subtitle:'Condizioni attuali', kind:'core', description:'Condizioni atmosferiche aggiornate quando il backend ha accesso a una fonte meteo.', examples:['Che tempo fa a Roma?','Com’è il meteo a Milano?'], showcase:{q:'Che tempo fa a Roma?',a:()=>'Leggo le condizioni attuali di Roma da una fonte meteo.'} },
    { id:'calcolatrice', title:'Calcolatrice', subtitle:'Operazioni e formule', kind:'future', status:'In arrivo', description:'Una capacità prevista per calcoli e formule. Non è ancora uno strumento disponibile nel backend.', examples:[] },
  ];

  const icons = {
    automatico:`<svg viewBox="0 0 96 96" fill="none" aria-hidden="true"><circle cx="48" cy="48" r="13" fill="#E2EFFF" stroke="#3578DA" stroke-width="2.5"/><circle cx="48" cy="48" r="7" fill="#F0A22C"/><g class="tool-orbit"><ellipse cx="48" cy="48" rx="38" ry="18" transform="rotate(-35 48 48)" stroke="#3173DA" stroke-width="2.5"/><ellipse cx="48" cy="48" rx="38" ry="18" transform="rotate(35 48 48)" stroke="#8BB8F3" stroke-width="2.5"/><ellipse cx="48" cy="48" rx="38" ry="18" transform="rotate(90 48 48)" stroke="#3173DA" stroke-width="2.1"/><circle cx="78" cy="27" r="5.7" fill="#F3A129"/><circle cx="30" cy="14" r="3" fill="#7EB2FA"/></g></svg>`,
    ora:`<svg viewBox="0 0 96 96" fill="none" aria-hidden="true"><circle cx="48" cy="48" r="36" fill="#F5F9FF" stroke="#2B65CE" stroke-width="4"/><circle cx="48" cy="48" r="29" stroke="#D7E7FA" stroke-width="1.3" stroke-dasharray="2 13"/><path d="M48 18v5M48 73v5M18 48h5M73 48h5" stroke="#86ACEB" stroke-width="2" stroke-linecap="round"/><path d="M48 48 64 31" stroke="#285EB9" stroke-width="4.5" stroke-linecap="round"/><g class="tool-clock-hand"><path d="M48 48V27" stroke="#EF9D2F" stroke-width="4.5" stroke-linecap="round"/></g><circle cx="48" cy="48" r="5" fill="#2B65CE"/><circle cx="48" cy="48" r="2.5" fill="#F5F9FF"/></svg>`,
    conversioni:`<svg viewBox="0 0 96 96" fill="none" aria-hidden="true"><g class="tool-convert-arrow"><path d="M20 28h54l-10-9m10 9-10 9" stroke="#F1A127" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><path d="M76 46H22l10-9m-10 9 10 9" stroke="#3074DC" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g><rect x="11" y="62" width="74" height="21" rx="5" fill="#ECF4FF" stroke="#3378DA" stroke-width="3"/><path d="M20 63v10m9-10v6m9-6v10m9-10v6m9-6v10m9-10v6m9-6v10" stroke="#2D66C3" stroke-width="2.2" stroke-linecap="round"/></svg>`,
    meteo:`<svg viewBox="0 0 96 96" fill="none" aria-hidden="true"><g class="tool-weather-sun"><circle cx="39" cy="38" r="20" fill="#F4AA31"/><path d="M39 6v7M39 63v7M7 38h8m48 0h8M16 15l7 7m33 33 7 7M63 15l-7 7M23 55l-7 7" stroke="#F5AF37" stroke-width="3.6" stroke-linecap="round"/></g><path d="M36 73h38c11 0 17-7 17-16 0-9-7-16-16-16-3 0-6 .8-8 2-4-11-16-17-27-12-8 3-13 11-13 19-8 0-13 5-13 12 0 7 6 11 22 11Z" fill="#6FAAF3"/><path d="M36 73h38c11 0 17-7 17-16 0-9-7-16-16-16-3 0-6 .8-8 2-4-11-16-17-27-12-8 3-13 11-13 19-8 0-13 5-13 12 0 7 6 11 22 11Z" fill="url(#cloudGrad)"/><defs><linearGradient id="cloudGrad" x1="26" x2="83" y1="37" y2="74"><stop stop-color="#B8DAFF"/><stop offset="1" stop-color="#3379DE"/></linearGradient></defs></svg>`,
    calcolatrice:`<svg viewBox="0 0 96 96" fill="none" aria-hidden="true"><rect x="23" y="8" width="50" height="80" rx="11" fill="#F1F7FF" stroke="#2E6ED5" stroke-width="4"/><rect x="31" y="17" width="34" height="18" rx="4" fill="#B9D6FC"/><path d="M36 26h23" stroke="#2A64CE" stroke-width="2.5" stroke-linecap="round"/><g fill="#4C8BE9"><rect x="31" y="44" width="10" height="10" rx="3"/><rect x="47" y="44" width="10" height="10" rx="3"/><rect x="31" y="60" width="10" height="10" rx="3"/><rect x="47" y="60" width="10" height="10" rx="3"/></g><rect class="tool-calculator-key" x="62" y="44" width="10" height="26" rx="4" fill="#F0A12A"/></svg>`,
  };
  const labIcon = `<svg viewBox="0 0 24 24" aria-hidden="true" width="21" height="21" fill="none"><path d="M9 3h6M10 3v7l-5 8a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-8V3M7 16h10" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  function timeStamp(){ return new Intl.DateTimeFormat('it-IT',{hour:'2-digit',minute:'2-digit'}).format(new Date()); }
  function notify(msg){ const node=$('toast'); node.textContent=msg; node.classList.add('is-visible'); clearTimeout(state.toastTimer); state.toastTimer=setTimeout(()=>node.classList.remove('is-visible'),3200); }
  function selectCapability(id){
    const tool=capabilities.find(x=>x.id===id); if(!tool) return;
    state.selected=id;
    document.querySelectorAll('.tool-card').forEach(b=>{const active=b.dataset.tool===id;b.classList.toggle('is-selected',active);b.setAttribute('aria-pressed',String(active));});
    $('detailIcon').innerHTML=icons[id];$('detailEyebrow').textContent=tool.kind==='future'?'PROSSIMAMENTE / ROADMAP':'ESPLORA / '+(capabilities.indexOf(tool)+1).toString().padStart(2,'0');$('detailTitle').textContent=tool.kind==='future'?'In arrivo: '+tool.title:tool.title==='Automatico'?'Una domanda, lo strumento giusto':tool.title+' nel tuo laboratorio';$('detailDescription').textContent=tool.description;
    $('exampleList').replaceChildren();
    if(!tool.examples.length){ const label=document.createElement('p');label.className='example-empty';label.textContent='Non ancora disponibile. Nessuna funzione da attivare.';$('exampleList').append(label); }
    for(const question of tool.examples){const button=document.createElement('button');button.className='example-button';button.type='button';button.textContent=question;button.addEventListener('click',()=>fillQuestion(question));$('exampleList').append(button);}
  }
  function renderTools(){
    $('toolGrid').replaceChildren();
    for (const tool of capabilities){
      const button=document.createElement('button');button.type='button';button.className='tool-card'+(tool.kind==='future'?' is-future':'');button.dataset.tool=tool.id;button.setAttribute('aria-pressed','false');button.setAttribute('aria-label',tool.title+(tool.kind==='future'?', funzionalità prevista':'')+'; mostra esempi');
      const icon=document.createElement('span');icon.className='tool-icon';icon.innerHTML=icons[tool.id];button.append(icon);
      const name=document.createElement('strong');name.textContent=tool.title;button.append(name);
      const subtitle=document.createElement('small');subtitle.textContent=tool.subtitle;button.append(subtitle);
      if(tool.kind==='future'){const badge=document.createElement('span');badge.className='tool-chip';badge.textContent='IN ARRIVO';button.append(badge);}
      button.addEventListener('click',()=>selectCapability(tool.id));$('toolGrid').append(button);
    }
    $('capabilityCount').textContent='/ '+String(capabilities.length).padStart(2,'0');selectCapability('automatico');
  }
  // Vetrina nell'hero: ruota una domanda per ogni strumento davvero disponibile (kind !== 'future', con `showcase`).
  // Le risposte sono esempi: l'ora è calcolata dal browser, nessun dato meteo inventato.
  function startShowcase(){
    const box=$('showcase'); if(!box) return;
    const items=capabilities.filter(t=>t.kind!=='future'&&t.showcase); if(!items.length){box.hidden=true;return;}
    const reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dots=$('scDots'); dots.replaceChildren(...items.map(()=>document.createElement('i')));
    let n=-1,paused=false;
    function show(){
      n=(n+1)%items.length; const t=items[n];
      $('scQuestion').textContent=t.showcase.q; $('scIcon').innerHTML=icons[t.id];
      $('scTool').textContent='STRUMENTO / '+t.title.toUpperCase(); $('scAnswer').textContent=t.showcase.a();
      [...dots.children].forEach((d,i)=>d.classList.toggle('on',i===n));
      box.classList.remove('is-in'); void box.offsetWidth; box.classList.add('is-in');
    }
    show();
    if(reduce||items.length<2) return; // niente rotazione automatica con prefers-reduced-motion
    box.addEventListener('mouseenter',()=>{paused=true;}); box.addEventListener('mouseleave',()=>{paused=false;});
    setInterval(()=>{ if(!paused&&!document.hidden&&state.view==='home') show(); },6000);
  }
  function fillQuestion(q){ $('questionInput').value=q;resizeInput();$('questionInput').focus(); }
  function resizeInput(){const ta=$('questionInput');ta.style.height='auto';ta.style.height=Math.min(150,Math.max(35,ta.scrollHeight))+'px';}
  function setView(v){state.view=v;$('app').dataset.view=v;for(const id of ['hero','capabilities','detailPanel'])$(id).hidden=v!=='home';$('conversationView').hidden=v!=='conversation';requestAnimationFrame(()=>{if(v==='conversation')$('messages').scrollTop=$('messages').scrollHeight;});}
  function addMessage(role,text,extra={}){
    const item={role,text,tool:extra.tool||'',demo:!!extra.demo,error:!!extra.error,loading:!!extra.loading,time:timeStamp()};state.messages.push(item);
    const article=document.createElement('article');article.className='message '+(role==='user'?'is-user':'is-assistant')+(item.error?' is-error':'');
    const avatar=document.createElement('div');avatar.className='message-avatar'+(role==='assistant'?' is-lab':'');avatar.setAttribute('aria-hidden','true');avatar.textContent=role==='user'?'♙':'✳';
    const bubble=document.createElement('div');bubble.className='message-bubble';const textNode=document.createElement('p');textNode.className='message-text';
    if(item.loading){const dots=document.createElement('span');dots.className='loading-dots';dots.setAttribute('aria-label','L’assistente sta rispondendo');for(let i=0;i<3;i++)dots.append(document.createElement('span'));textNode.append(dots);}else{textNode.textContent=text;}
    bubble.append(textNode);
    const meta=document.createElement('div');meta.className='message-meta';
    if(item.tool){const label=document.createElement('span');label.className='tool-used';label.textContent=(item.demo?'Dimostrazione: ':'Strumento: ')+item.tool;meta.append(label);}
    if(item.demo&&!item.tool){const label=document.createElement('span');label.className='tool-used';label.textContent='Risposta dimostrativa';meta.append(label);}
    const ts=document.createElement('time');ts.textContent=item.time;meta.append(ts);bubble.append(meta);
    article.append(avatar,bubble);$('messages').append(article);$('messages').scrollTop=$('messages').scrollHeight;
    return {article,textNode,item};
  }
  function getDemoAnswer(text){
    const q=text.toLowerCase();
    if(/(tokyo|tokio|new york|londra|london|roma|parigi)/.test(q)&&/(ore|ora|orario|fuso)/.test(q)){
      const city=/tokyo|tokio/.test(q)?['Tokyo','Asia/Tokyo']:/new york/.test(q)?['New York','America/New_York']:/londra|london/.test(q)?['Londra','Europe/London']:/parigi/.test(q)?['Parigi','Europe/Paris']:['Roma','Europe/Rome'];
      const t=new Intl.DateTimeFormat('it-IT',{timeZone:city[1],hour:'2-digit',minute:'2-digit'}).format(new Date());
      return {reply:`A ${city[0]} sono le ${t}.\nOra calcolata dal browser per mostrare l'aspetto della risposta, non da un modello linguistico.`,tool:'Ora',demo:true};
    }
    if(/(5000|5\s*000)/.test(q)&&/(km|chilometri|metri|\bm\b)/.test(q))return {reply:'5000 metri corrispondono a 5 chilometri.\nQuesto risultato è calcolato dalla demo, non dal modello.',tool:'Conversioni',demo:true};
    if(/25/.test(q)&&/(fahrenheit|°f|celsius|°c)/.test(q))return {reply:'25 °C equivalgono a 77 °F.\nQuesto risultato è calcolato dalla demo, non dal modello.',tool:'Conversioni',demo:true};
    if(/(meteo|tempo fa|piove|temperatura|previsioni)/.test(q))return {reply:'Per conoscere il meteo reale occorre collegare il backend e la relativa fonte dati. In questa anteprima non vengono inventate condizioni meteorologiche.',demo:true};
    if(/(calcol|quanto fa|formula|\d\s*[+*×÷/-]\s*\d)/.test(q))return {reply:'La calcolatrice è prevista fra i prossimi strumenti. La scheda è una proposta UI, non una funzione già disponibile.',demo:true};
    return {reply:'Questa è un’anteprima interattiva dell’interfaccia. Per ricevere risposte dal modello locale collega l’endpoint del backend in config.js. Le schede non forzano nessuno strumento.',demo:true};
  }
  async function callBackend(message,history,signal){
    const response=await fetch(conf.endpoint,{method:'POST',headers:{'Content-Type':'application/json',...(conf.headers||{})},body:JSON.stringify({message,history}),signal});
    if(!response.ok)throw new Error('Il backend ha risposto con HTTP '+response.status+'.');
    const data=await response.json();
    const reply=typeof data==='string'?data:(data.reply??data.response??data.answer??data.message??data.content);
    if(typeof reply!=='string'||!reply.trim())throw new Error('Formato della risposta non riconosciuto: verifica l’adattatore nel file app.js.');
    let tool=data.tool_used??data.tool??data.tools??'';
    if(Array.isArray(tool))tool=tool.map(x=>typeof x==='string'?x:(x&&x.name)||'').filter(Boolean).join(', ');
    else if(tool&&typeof tool==='object')tool=tool.name||'';
    return {reply,tool:String(tool).slice(0,120),demo:false};
  }
  async function submitQuestion(question){
    const q=String(question||'').trim();if(!q||state.pending)return;
    const history=state.messages.filter(m=>!m.loading&&!m.error).map(m=>({role:m.role,content:m.text}));
    setView('conversation');addMessage('user',q);$('questionInput').value='';resizeInput();state.pending=true;$('sendButton').disabled=true;
    const loading=addMessage('assistant','',{loading:true});
    const ctrl=new AbortController();state.controller=ctrl;
    const timer=setTimeout(()=>ctrl.abort('timeout'),Number(conf.timeoutMs)||60000);
    try{
      const result=isApi?await callBackend(q,history,ctrl.signal):await new Promise(resolve=>setTimeout(()=>resolve(getDemoAnswer(q)),650));
      if(!loading.article.isConnected)return;
      loading.article.remove();state.messages.pop();addMessage('assistant',result.reply,{tool:result.tool,demo:result.demo});
    }catch(err){
      if(!loading.article.isConnected)return;
      loading.article.remove();state.messages.pop();const reason=err?.name==='AbortError'?'Richiesta interrotta o scaduta.':(err?.message||'Errore sconosciuto');
      const fail=addMessage('assistant','Impossibile ottenere una risposta. '+reason,{error:true});
      const retry=document.createElement('button');retry.type='button';retry.className='retry-button';retry.textContent='Riprova';retry.addEventListener('click',()=>{if(state.pending)return;fail.article.remove();state.messages.pop();state.messages.pop();$('messages').lastElementChild?.remove();submitQuestion(q);});fail.textNode.after(retry);
    }finally{clearTimeout(timer);if(state.controller===ctrl)state.controller=null;state.pending=false;$('sendButton').disabled=false;$('questionInput').focus();}
  }
  function newConversation(){state.controller?.abort();state.controller=null;state.messages=[];state.pending=false;$('messages').replaceChildren();$('sendButton').disabled=false;setView('home');$('questionInput').value='';resizeInput();window.scrollTo({top:0,behavior:'smooth'});notify('Nuova conversazione temporanea.');}
  function openHelp(){ $('helpDialog').showModal(); }
  function init(){
    renderTools();startShowcase();
    $('connectionStatus').querySelector('span:last-child').textContent=isApi?'Backend configurato':'Interfaccia demo';
    $('connectionStatus').classList.toggle('is-configured',isApi);
    $('backendNote').textContent=isApi?'Risposte tramite il backend configurato.':'Anteprima UI: nessun modello collegato.';
    $('questionForm').addEventListener('submit',e=>{e.preventDefault();submitQuestion($('questionInput').value);});
    $('questionInput').addEventListener('input',resizeInput);
    $('questionInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();submitQuestion($('questionInput').value);}});
    $('navChat').addEventListener('click',()=>{if(state.messages.length)setView('conversation');$('questionInput').focus();});
    $('backHome').addEventListener('click',()=>{setView('home');window.scrollTo(0,0);});
    for(const logo of document.querySelectorAll('.brand-mark, .mobile-mark'))logo.addEventListener('click',e=>{e.preventDefault();setView('home');window.scrollTo(0,0);});
    $('navTools').addEventListener('click',()=>{if(state.view==='conversation'){notify('Le capacità vengono selezionate automaticamente durante la chat.');return;}$('capabilities').scrollIntoView({behavior:'smooth',block:'center'});});
    for(const id of ['navHelp','topHelp'])$(id).addEventListener('click',openHelp);
    $('closeHelp').addEventListener('click',()=>$('helpDialog').close());$('helpOk').addEventListener('click',()=>$('helpDialog').close());
    $('newConversation').addEventListener('click',newConversation);
    $('toggleAllTools').addEventListener('click',()=>{state.expanded=!state.expanded;$('toggleAllTools').setAttribute('aria-expanded',String(state.expanded));$('toggleAllTools').innerHTML=state.expanded?'Vista compatta <span aria-hidden="true">↗</span>':'Tutte le capacità <span aria-hidden="true">↗</span>';$('toolViewport').style.overflow=state.expanded?'visible':'';$('toolGrid').style.cssText=state.expanded?'grid-auto-flow:row;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));min-width:0;':'';notify(state.expanded?'Tutte le capacità disponibili e previste.':'Torna alla panoramica scorrevole.');});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
