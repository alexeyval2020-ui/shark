(function(){
  var LG=window.SHARK_DATA.leagues;
  var M=window.SHARK_DATA.matches.map(function(r,i){
    return {id:i,lg:r[0],ts:Date.parse(r[1]+':00+03:00'),h:r[2],a:r[3],st:r[4]||'',hg:(r[5]==null?null:r[5]),ag:(r[6]==null?null:r[6]),fx:r[7]||0,hid:r[8]||0,aid:r[9]||0,day:r[1].slice(0,10),time:r[1].slice(11)};
  });
  M.sort(function(x,y){return x.ts-y.ts||LG[x.lg].o-LG[y.lg].o;});

  var KEY='sharkru-v1';
  var st={fav:{},pick:{}};
  try{var s=JSON.parse(localStorage.getItem(KEY)||'null');if(s&&s.fav&&s.pick)st=s;}catch(e){}
  function save(){try{localStorage.setItem(KEY,JSON.stringify(st));}catch(e){}}

  function $(s){return document.querySelector(s);}
  var MON=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
  var WD=['вс','пн','вт','ср','чт','пт','сб'];
  function mskToday(){return new Date(Date.now()+3*3600e3).toISOString().slice(0,10);}
  var days=[];M.forEach(function(m){if(days.indexOf(m.day)<0)days.push(m.day);});
  var today=mskToday();
  var view={day:days.filter(function(d){return d>=today;})[0]||days[days.length-1],lg:'all',q:'',favOnly:false};

  function dparts(d){var dt=new Date(d+'T12:00:00Z');return {wd:WD[dt.getUTCDay()],d:dt.getUTCDate(),m:MON[dt.getUTCMonth()]};}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}

  function renderStrip(){
    $('#strip').innerHTML=days.map(function(d){
      var p=dparts(d),on=d===view.day;
      return '<button class="day" data-d="'+d+'" aria-pressed="'+on+'"><span>'+(d===today?'сегодня':p.wd)+'</span><b>'+p.d+' '+p.m+'</b></button>';
    }).join('');
  }
  function renderChips(){
    var ids=['all'].concat(Object.keys(LG).sort(function(a,b){return LG[a].o-LG[b].o;}));
    var h=ids.map(function(id){
      return '<button class="chip" data-l="'+id+'" aria-pressed="'+(view.lg===id)+'">'+(id==='all'?'Все лиги':LG[id].n)+'</button>';
    }).join('');
    h+='<button class="chip" data-fav="1" aria-pressed="'+view.favOnly+'">★ Избранное</button>';
    $('#chips').innerHTML=h;
  }
  var FIN=['FT','AET','PEN'],LIVE=['1H','HT','2H','ET','BT','P','LIVE','INT','SUSP'];
  function hasScore(m){return m.hg!=null&&m.ag!=null&&m.st!=='NS'&&m.st!=='TBD'&&m.st!=='PST'&&m.st!=='CANC';}
  function status(m){
    var now=Date.now(),diff=m.ts-now;
    if(FIN.indexOf(m.st)>=0)return {t:m.st==='FT'?'завершён':(m.st==='AET'?'доп. время':'пенальти'),c:'done'};
    if(LIVE.indexOf(m.st)>=0)return {t:m.st==='HT'?'перерыв':'идёт',c:'live'};
    if(m.st==='PST')return {t:'перенесён',c:''};
    if(m.st==='CANC'||m.st==='ABD')return {t:'отменён',c:''};
    if(diff>0){
      var mins=Math.round(diff/60000);
      if(mins<60)return {t:'через '+mins+' мин',c:'live'};
      if(mins<24*60)return {t:'через '+Math.floor(mins/60)+' ч '+(mins%60)+' м',c:''};
      return {t:'',c:''};
    }
    return {t:'начался',c:'live'};
  }
  function renderList(){
    var q=view.q.trim().toLowerCase();
    var L=M.filter(function(m){
      if(m.day!==view.day)return false;
      if(view.lg!=='all'&&m.lg!==view.lg)return false;
      if(view.favOnly&&!st.fav[m.id])return false;
      if(q&&(m.h+' '+m.a).toLowerCase().indexOf(q)<0)return false;
      return true;
    });
    var p=dparts(view.day);
    $('#count').textContent=p.d+' '+p.m+', матчей: '+L.length;
    var picks=Object.keys(st.pick).length;
    $('#mine').textContent='Моих прогнозов: '+picks;
    if(!L.length){
      $('#list').innerHTML='<div class="empty">'+(view.favOnly?'В избранном на этот день пусто. Нажми ☆ у матча.':'Под этот фильтр матчей нет. Смени лигу или очисти поиск.')+'</div>';
      return;
    }
    var h='',last='';
    L.sort(function(x,y){return LG[x.lg].o-LG[y.lg].o||x.ts-y.ts;}).forEach(function(m){
      if(m.lg!==last){last=m.lg;h+='<h2 class="lg">'+LG[m.lg].n+' <i>'+LG[m.lg].c+'</i></h2>';}
      var s=status(m),pk=st.pick[m.id],fv=!!st.fav[m.id];
      h+='<div class="row"><div class="t" data-open="'+m.id+'">'+m.time+(s.t?'<small class="'+s.c+'">'+s.t+'</small>':'')+'</div>'+
        '<div class="teams" data-open="'+m.id+'" tabindex="0" role="button" aria-label="Подробности матча"><span><b>'+esc(m.h)+'</b>'+(hasScore(m)?'<em class="sc">'+m.hg+'</em>':'')+'</span><span><b>'+esc(m.a)+'</b>'+(hasScore(m)?'<em class="sc">'+m.ag+'</em>':'')+'</span></div>'+
        '<div class="side"><div class="pk" role="group" aria-label="Мой прогноз">'+
        ['1','X','2'].map(function(k){return '<button data-pk="'+m.id+'" data-k="'+k+'" aria-pressed="'+(pk===k)+'" aria-label="Прогноз '+(k==='1'?'победа хозяев':k==='X'?'ничья':'победа гостей')+'">'+(k==='X'?'Х':'П'+k)+'</button>';}).join('')+
        '</div><button class="star" data-fav="'+m.id+'" aria-pressed="'+fv+'" aria-label="'+(fv?'Убрать из избранного':'В избранное')+'">'+(fv?'★':'☆')+'</button></div></div>';
    });
    $('#list').innerHTML=h;
  }
  function all(){renderStrip();renderChips();renderList();}

  $('#strip').addEventListener('click',function(e){
    var b=e.target.closest('.day');if(!b)return;view.day=b.dataset.d;all();
  });
  $('#chips').addEventListener('click',function(e){
    var b=e.target.closest('.chip');if(!b)return;
    if(b.dataset.fav){view.favOnly=!view.favOnly;}else{view.lg=b.dataset.l;}
    renderChips();renderList();
  });
  $('#q').addEventListener('input',function(e){view.q=e.target.value;renderList();});
  $('#list').addEventListener('click',function(e){
    var o=e.target.closest('[data-open]');
    if(o){openMatch(+o.dataset.open);return;}
    var s=e.target.closest('.star'),p=e.target.closest('[data-pk]');
    if(s){var id=s.dataset.fav;if(st.fav[id])delete st.fav[id];else st.fav[id]=1;save();renderList();}
    else if(p){var id2=p.dataset.pk,k=p.dataset.k;if(st.pick[id2]===k)delete st.pick[id2];else st.pick[id2]=k;save();renderList();}
  });

  /* ---------- карточка матча ---------- */
  var POS={G:'В',D:'З',M:'П',F:'Н'};
  var cur=null,tab='ov';
  function byMid(id){return M.filter(function(m){return m.id===id;})[0];}
  function dd(){return (window.SHARK_DETAILS||{})[cur.fx]||{};}
  function form(f){
    if(!f)return '<span class="mu">нет данных</span>';
    return f.split('').slice(-5).map(function(c){return '<i class="fm '+c+'">'+(c==='W'?'В':c==='D'?'Н':'П')+'</i>';}).join('');
  }
  function noData(t){return '<p class="nd">'+t+'</p>';}
  function vOverview(){
    var T=window.SHARK_TEAMS||{},h=T[cur.hid],a=T[cur.aid];
    if(!h||!a)return noData('Таблицы для этого турнира нет или она ещё не загружена. Она обновляется раз в сутки для РПЛ, Премьер-лиги, Ла Лиги, Серии A, Бундеслиги и Лиги 1.');
    function row(l,x,y){return '<tr><td>'+x+'</td><th scope="row">'+l+'</th><td>'+y+'</td></tr>';}
    return '<div class="tbl"><table><thead><tr><th>'+esc(cur.h)+'</th><th></th><th>'+esc(cur.a)+'</th></tr></thead><tbody>'+
      row('Место в таблице',h.rank,a.rank)+row('Очки',h.pts,a.pts)+row('Игры',h.p,a.p)+
      row('Победы / ничьи / поражения',h.w+' / '+h.d+' / '+h.l,a.w+' / '+a.d+' / '+a.l)+
      row('Голы (забито : пропущено)',h.gf+' : '+h.ga,a.gf+' : '+a.ga)+
      row('Последние матчи',form(h.form),form(a.form))+'</tbody></table></div>';
  }
  function vH2h(){
    var L=dd().h2h;
    if(!L)return noData('Прошлые встречи загружаются заранее для матчей в ближайшие сутки.');
    if(!L.length)return noData('Раньше эти команды не встречались или данных нет.');
    var wh=0,wa=0,dr=0;
    L.forEach(function(x){
      if(x.hg==null||x.ag==null)return;
      if(x.hg===x.ag){dr++;return;}
      var win=x.hg>x.ag?x.h:x.a;
      if(win===cur.h)wh++;else if(win===cur.a)wa++;
    });
    return '<p class="sum"><b>'+esc(cur.h)+'</b> '+wh+' · ничьих '+dr+' · '+wa+' <b>'+esc(cur.a)+'</b> <span class="mu">(последние '+L.length+')</span></p><ul class="h2h">'+
      L.map(function(x){
        var d=x.d.slice(8,10)+'.'+x.d.slice(5,7)+'.'+x.d.slice(0,4);
        return '<li><span class="mu">'+d+' · '+esc(x.lg)+'</span><span>'+esc(x.h)+' <b class="sc">'+(x.hg==null?'-':x.hg)+':'+(x.ag==null?'-':x.ag)+'</b> '+esc(x.a)+'</span></li>';
      }).join('')+'</ul>';
  }
  function side(n,s){
    if(!s)return '<div><h3>'+esc(n)+'</h3>'+'<p class="mu">нет данных</p></div>';
    var pl=function(L){return L.map(function(p){return '<li><b>'+(p[0]===''?'':p[0])+'</b> '+esc(p[1])+(p[2]?' <span class="mu">'+(POS[p[2]]||p[2])+'</span>':'')+'</li>';}).join('');};
    return '<div><h3>'+esc(n)+'</h3><p class="mu">'+(s.f?'Схема '+esc(s.f):'')+(s.c?' · тренер '+esc(s.c):'')+'</p><ol class="pl">'+pl(s.xi)+'</ol>'+(s.s&&s.s.length?'<p class="mu">Запасные</p><ol class="pl">'+pl(s.s)+'</ol>':'')+'</div>';
  }
  function vLineups(){
    var lu=dd().lu;
    if(!lu)return noData('Составы появляются примерно за час до начала матча.');
    return '<div class="two">'+side(cur.h,lu.home)+side(cur.a,lu.away)+'</div>';
  }
  function renderModal(){
    var m=cur,s=status(m),sc=hasScore(m)?m.hg+' : '+m.ag:'vs';
    var body=!m.fx?noData('Для этого матча подробные данные недоступны.'):(tab==='ov'?vOverview():tab==='h2h'?vH2h():vLineups());
    var p=dparts(m.day);
    $('#modal-box').innerHTML='<button class="x" id="mx" aria-label="Закрыть">×</button>'+
      '<div class="mu">'+LG[m.lg].n+' · '+p.d+' '+p.m+', '+m.time+(s.t?' · '+s.t:'')+'</div>'+
      '<div class="mh"><span>'+esc(m.h)+'</span><b class="big">'+sc+'</b><span>'+esc(m.a)+'</span></div>'+
      '<div class="mtabs" role="tablist">'+[['ov','Статистика'],['h2h','Встречи'],['lu','Составы']].map(function(t){return '<button role="tab" data-tab="'+t[0]+'" aria-selected="'+(tab===t[0])+'">'+t[1]+'</button>';}).join('')+'</div>'+
      '<div class="mbody">'+body+'</div>';
    $('#mx').focus();
  }
  function openMatch(id){
    cur=byMid(id);if(!cur)return;tab='ov';
    $('#modal').hidden=false;document.body.style.overflow='hidden';renderModal();
  }
  function closeModal(){$('#modal').hidden=true;document.body.style.overflow='';}
  $('#modal').addEventListener('click',function(e){
    if(e.target.id==='modal'||e.target.id==='mx'){closeModal();return;}
    var b=e.target.closest('[data-tab]');if(b){tab=b.dataset.tab;renderModal();}
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&!$('#modal').hidden)closeModal();
    if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('.teams[data-open]')){e.preventDefault();openMatch(+e.target.dataset.open);}
  });
  setInterval(renderList,60000);
  all();
})();
