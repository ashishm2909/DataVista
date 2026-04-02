/* DataVista Core — Vanilla JS, no jQuery */
(function(){
  'use strict';
  var charts={};

  document.addEventListener('DOMContentLoaded',function(){
    var ld=document.getElementById('pageLoader');
    if(ld) requestAnimationFrame(function(){ ld.classList.add('done'); setTimeout(function(){ld.remove()},500); });
    initReveal();
    initNavScroll();
    initCharts();
  });

  function initReveal(){
    var els=document.querySelectorAll('.rv');
    if(!els.length) return;
    var obs=new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('on'); obs.unobserve(e.target); }});
    },{threshold:0.08,rootMargin:'0px 0px -30px 0px'});
    els.forEach(function(el){ obs.observe(el); });
  }

  function initNavScroll(){
    var nav=document.getElementById('mainNav');
    if(!nav) return;
    var ticking=false;
    window.addEventListener('scroll',function(){
      if(!ticking){ requestAnimationFrame(function(){ nav.classList.toggle('scrolled',window.scrollY>20); ticking=false; }); ticking=true; }
    });
  }

  function initCharts(){
    document.querySelectorAll('.chart-cv canvas').forEach(function(cv){
      var id=cv.dataset.chartId;
      if(id && window.chartData && window.chartData[id]) createChart(cv,window.chartData[id]);
    });
  }

  function applyDefaults(d){
    // Base defaults — chart_service.py now provides most options,
    // so we only fill in gaps here
    var defs={
      responsive:true,
      maintainAspectRatio:false,
      animation:{duration:700,easing:'easeOutQuart'},
      plugins:{
        legend:{
          labels:{
            color:'#6b7a99',
            font:{family:'Inter',size:11},
            padding:12,
            usePointStyle:true,
            pointStyleWidth:7
          }
        },
        tooltip:{
          backgroundColor:'rgba(22,28,42,0.95)',
          titleColor:'#e8edf5',
          bodyColor:'#6b7a99',
          borderColor:'rgba(0,240,255,0.15)',
          borderWidth:1,
          cornerRadius:8,
          padding:10,
          titleFont:{family:'Inter',size:12,weight:600},
          bodyFont:{family:'Inter',size:11},
          displayColors:true,
          boxPadding:4
        }
      }
    };
    if(!d.options) d.options={};
    // Merge: service options take priority over defaults
    d.options=merge(defs,d.options);
    // Apply scale theme if scales exist and don't already have full config
    if(d.options.scales){
      var axTheme={
        color:'#6b7a99',
        font:{family:'Inter',size:10},
        grid:{color:'rgba(30,42,66,0.5)'},
        border:{color:'rgba(30,42,66,0.5)'}
      };
      ['x','y'].forEach(function(axis){
        if(d.options.scales[axis]){
          d.options.scales[axis]=merge(axTheme,d.options.scales[axis]);
        }
      });
    }
    return d;
  }
  function merge(t,s){ var r={}; for(var k in t) r[k]=t[k]; for(var k in s){ if(s[k]&&typeof s[k]==='object'&&!Array.isArray(s[k])) r[k]=merge(r[k]||{},s[k]); else r[k]=s[k]; } return r; }

  function createChart(cv,data){
    if(!cv) return null;
    if(typeof cv==='string') cv=document.getElementById(cv);
    if(!cv) return null;
    try{
      var ctx=cv.getContext('2d'), id=cv.dataset.chartId||cv.id||'c'+Date.now();
      if(charts[id]) charts[id].destroy();
      charts[id]=new Chart(ctx,applyDefaults(data));
      return charts[id];
    }catch(e){ console.error(e); return null; }
  }

  function destroyChart(id){ if(charts[id]){ charts[id].destroy(); delete charts[id]; } }

  function getCookie(n){ var v='; '+document.cookie, p=v.split('; '+n+'='); return p.length===2 ? p.pop().split(';').shift() : ''; }

  function toast(msg,type){
    type=type||'info';
    var c=document.getElementById('toasts');
    if(!c) return;
    var icons={success:'fa-check-circle',danger:'fa-circle-xmark',warning:'fa-triangle-exclamation',info:'fa-circle-info'};
    var colors={success:'var(--lime)',danger:'var(--red)',warning:'var(--amber)',info:'var(--cyan)'};
    var el=document.createElement('div');
    el.className='toast-item';
    el.style.borderLeft='3px solid '+colors[type];
    el.innerHTML='<i class="fas '+(icons[type]||icons.info)+' toast-icon" style="color:'+colors[type]+'"></i><span>'+msg+'</span><button class="toast-close" onclick="this.parentElement.classList.add(\'out\');setTimeout(function(){this.parentElement.remove()}.bind(this),300)"><i class="fas fa-xmark"></i></button>';
    c.appendChild(el);
    setTimeout(function(){ el.classList.add('out'); setTimeout(function(){el.remove()},300); },4000);
  }

  function formatSize(b){ if(!b) return'0 B'; var k=1024,s=['B','KB','MB','GB'],i=Math.floor(Math.log(b)/Math.log(k)); return(parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]); }

  function validateType(f,types){ return types.indexOf('.'+f.name.split('.').pop().toLowerCase())>-1; }

  window.DV={
    toast:toast,
    createChart:createChart,
    destroyChart:destroyChart,
    getCookie:getCookie,
    formatSize:formatSize,
    validateType:validateType,
    showLoading:function(el){ if(!el)return; el._h=el.innerHTML; el.innerHTML='<div class="d-flex justify-content-center align-items-center" style="height:80px"><div class="loader-ring" style="width:28px;height:28px;border-width:2px"></div></div>'; },
    hideLoading:function(el){ if(!el||!el._h)return; el.innerHTML=el._h; }
  };
})();
