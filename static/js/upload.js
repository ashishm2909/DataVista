/* DataVista Upload — Vanilla JS, fetch API, cookie-based CSRF */
(function(){
  'use strict';

  document.addEventListener('DOMContentLoaded',function(){
    var area=document.getElementById('uploadArea');
    var input=document.getElementById('fileInput');
    if(!area||!input) return;

    // Drag events
    ['dragenter','dragover'].forEach(function(ev){
      area.addEventListener(ev,function(e){ e.preventDefault(); e.stopPropagation(); area.classList.add('dragover'); });
    });
    ['dragleave','drop'].forEach(function(ev){
      area.addEventListener(ev,function(e){ e.preventDefault(); e.stopPropagation(); area.classList.remove('dragover'); });
    });
    area.addEventListener('drop',function(e){
      var files=e.dataTransfer&&e.dataTransfer.files;
      if(files&&files.length) handleFile(files[0]);
    });

    // Click
    input.addEventListener('change',function(e){ if(e.target.files.length) handleFile(e.target.files[0]); });
    area.addEventListener('click',function(e){
      if(e.target.tagName!=='BUTTON'&&e.target.tagName!=='INPUT') input.click();
    });
  });

  function handleFile(file){
    var exts=['.xlsx','.xls','.csv','.sql'];
    var ext='.'+file.name.split('.').pop().toLowerCase();
    if(exts.indexOf(ext)===-1){ DV.toast('Unsupported file type. Use Excel, CSV, or SQL.','danger'); return; }
    if(file.size>100*1024*1024){ DV.toast('File exceeds 100MB limit.','danger'); return; }
    uploadFile(file);
  }

  function getCSRF(){
    return DV.getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]')||{}).value || '';
  }

  function uploadFile(file){
    var prog=document.getElementById('uploadProgress');
    var result=document.getElementById('uploadResult');
    var nameEl=document.getElementById('fileName');
    var bar=prog.querySelector('.progress-fill');
    var pct=prog.querySelector('.upload-percentage');

    prog.style.display='block';
    result.style.display='none';
    nameEl.textContent=file.name;
    bar.style.width='0%';
    pct.textContent='0%';

    var fd=new FormData();
    fd.append('file',file);

    var xhr=new XMLHttpRequest();
    xhr.open('POST','/upload/handle/',true);
    xhr.setRequestHeader('X-CSRFToken',getCSRF());
    xhr.setRequestHeader('X-Requested-With','XMLHttpRequest');

    xhr.upload.addEventListener('progress',function(e){
      if(e.lengthComputable){
        var p=Math.round((e.loaded/e.total)*100);
        bar.style.width=p+'%';
        pct.textContent=p+'%';
      }
    });

    xhr.onload=function(){
      prog.style.display='none';
      try{
        var res=JSON.parse(xhr.responseText);
        if(xhr.status>=200&&xhr.status<300&&res.success){
          showSuccess(res,file);
        } else {
          showError(res.error||'Upload failed');
        }
      } catch(e){
        showError('Server error. Please try again.');
      }
    };

    xhr.onerror=function(){
      prog.style.display='none';
      showError('Network error. Check your connection.');
    };

    xhr.send(fd);
  }

  function showSuccess(res,file){
    var el=document.getElementById('uploadResult');
    el.innerHTML='<div class="alert alert-ok">'+
      '<h6 style="font-weight:700;margin-bottom:0.4rem"><i class="fas fa-check-circle me-2"></i>Upload Successful!</h6>'+
      '<p style="margin-bottom:0.5rem;font-size:0.88rem">'+res.message+'</p>'+
      '<div style="display:flex;gap:1rem;font-size:0.82rem;color:var(--gray)">'+
        '<span><strong style="color:var(--white)">'+file.name+'</strong></span>'+
        '<span>'+DV.formatSize(file.size)+'</span>'+
        '<span>'+res.dataset_info.row_count.toLocaleString()+' rows</span>'+
        '<span>'+res.dataset_info.column_count+' columns</span>'+
      '</div>'+
      '<div style="margin-top:0.75rem;display:flex;gap:0.5rem">'+
        '<a href="/file/'+res.file_id+'/" class="btn btn-outline-cyan btn-sm"><i class="fas fa-eye me-1"></i>View Data</a>'+
        '<a href="/dashboard/create/'+res.file_id+'/" class="btn btn-cyan btn-sm"><i class="fas fa-chart-bar me-1"></i>Create Dashboard</a>'+
      '</div></div>';
    el.style.display='block';
    DV.toast('File uploaded and processed!','success');
    setTimeout(function(){ window.location.reload(); },3000);
  }

  function showError(msg){
    var el=document.getElementById('uploadResult');
    el.innerHTML='<div class="alert alert-err">'+
      '<h6 style="font-weight:700;margin-bottom:0.3rem"><i class="fas fa-circle-xmark me-2"></i>Upload Failed</h6>'+
      '<p style="margin:0;font-size:0.88rem">'+msg+'</p>'+
      '<div style="margin-top:0.5rem"><button class="btn btn-outline-danger btn-sm" onclick="retryUpload()"><i class="fas fa-rotate-right me-1"></i>Try Again</button></div></div>';
    el.style.display='block';
    DV.toast(msg,'danger');
  }

  window.retryUpload=function(){
    document.getElementById('uploadResult').style.display='none';
    var inp=document.getElementById('fileInput');
    inp.value='';
    inp.click();
  };
})();
