import React, { useState } from 'react';
import { ImagePlus, Scissors, Star, Trash2, WandSparkles } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? window.location.origin : '');
const rgbDistance = (a,b) => Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);

async function extractStickers(file,tolerance) {
  const bitmap=await createImageBitmap(file);
  const scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
  const w=Math.max(1,Math.round(bitmap.width*scale)), h=Math.max(1,Math.round(bitmap.height*scale));
  const canvas=document.createElement('canvas'); canvas.width=w; canvas.height=h;
  const ctx=canvas.getContext('2d',{willReadFrequently:true}); ctx.drawImage(bitmap,0,0,w,h); bitmap.close?.();
  const image=ctx.getImageData(0,0,w,h), px=image.data, total=w*h;
  const at=(x,y)=>{const i=(y*w+x)*4;return [px[i],px[i+1],px[i+2]];};
  // Estimate the backdrop from many border samples, not just four corners.
  // Per-channel medians ignore isolated artwork touching a corner.
  const border=[];
  const step=Math.max(1,Math.floor(Math.max(w,h)/180));
  for(let x=0;x<w;x+=step){border.push(at(x,0),at(x,h-1));}
  for(let y=0;y<h;y+=step){border.push(at(0,y),at(w-1,y));}
  const bg=[0,1,2].map(k=>{const values=border.map(v=>v[k]).sort((a,b)=>a-b);return values[Math.floor(values.length/2)]||255;});
  const removed=new Uint8Array(total), queue=new Int32Array(total); let head=0,tail=0;
  const add=i=>{if(i<0||i>=total||removed[i])return;const p=i*4;if(px[p+3]<8||rgbDistance([px[p],px[p+1],px[p+2]],bg)<=tolerance){removed[i]=1;queue[tail++]=i;}};
  for(let x=0;x<w;x++){add(x);add((h-1)*w+x);} for(let y=0;y<h;y++){add(y*w);add(y*w+w-1);}
  while(head<tail){const i=queue[head++],x=i%w,y=Math.floor(i/w);if(x)add(i-1);if(x+1<w)add(i+1);if(y)add(i-w);if(y+1<h)add(i+w);}
  for(let i=0;i<total;i++)if(removed[i])px[i*4+3]=0;
  ctx.putImageData(image,0,0);
  // Detect components from actual opaque pixels. Do not dilate the mask:
  // dilation can join neighbouring stickers and create oversized crops.
  const mask=new Uint8Array(total), seen=new Uint8Array(total);
  for(let i=0;i<total;i++)if(px[i*4+3]>24)mask[i]=1;
  const minArea=Math.max(45,Math.floor(total*.00002)), parts=[];
  for(let i=0;i<total;i++){if(!mask[i]||seen[i])continue;let qh=0,qt=0;queue[qt++]=i;seen[i]=1;let minX=w,minY=h,maxX=0,maxY=0,area=0;
    while(qh<qt){const n=queue[qh++],x=n%w,y=Math.floor(n/w);minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);area++;
      const ns=[n-1,n+1,n-w,n+w];for(const z of ns){if(z<0||z>=total||seen[z]||!mask[z]||Math.abs((z%w)-x)>1)continue;seen[z]=1;queue[qt++]=z;}}
    if(area>=minArea&&maxX-minX>8&&maxY-minY>8)parts.push({minX,minY,maxX,maxY});
  }
  parts.sort((a,b)=>a.minY-b.minY||a.minX-b.minX);
  return Promise.all(parts.map(async(p,index)=>{const pad=6,left=Math.max(0,p.minX-pad),top=Math.max(0,p.minY-pad),cw=Math.min(w-left,p.maxX-p.minX+pad*2+1),ch=Math.min(h-top,p.maxY-p.minY+pad*2+1);const out=document.createElement('canvas');out.width=cw;out.height=ch;out.getContext('2d').putImageData(ctx.getImageData(left,top,cw,ch),0,0);const blob=await new Promise(resolve=>out.toBlob(resolve,'image/png'));return {id:String(Date.now())+'-'+index,label:'Sticker '+(index+1),blob,preview:URL.createObjectURL(blob)};}));
}

export default function StickerStudio({connected,apiUrl,onSaved,setNotice}) {
 const [file,setFile]=useState(null),[tolerance,setTolerance]=useState(48),[items,setItems]=useState([]),[busy,setBusy]=useState(false),[saving,setSaving]=useState(false),[error,setError]=useState(''),[names,setNames]=useState({});
 async function process(){if(!file)return;setBusy(true);setError('');items.forEach(x=>URL.revokeObjectURL(x.preview));try{const found=await extractStickers(file,tolerance);setItems(found);setNames(Object.fromEntries(found.map(x=>[x.id,x.label])));if(!found.length)setError('No separate designs detected. Try a higher tolerance or a sheet with wider gaps.');}catch(e){setError(e.message||'Could not process this sheet.');}finally{setBusy(false);}}
 async function suggestNames(){if(!items.length)return;setNaming(true);setError('');const base=(apiUrl||API_BASE).replace(/\/$/,'');try{for(const item of items){const form=new FormData();form.append('file',item.blob,'sticker.png');const r=await fetch(base+'/v1/stickers/suggest-label',{method:'POST',body:form,credentials:'include'});if(!r.ok)throw new Error('Name suggestions are temporarily unavailable. You can still rename each sticker yourself.');const data=await r.json();if(data.label)setNames(v=>({...v,[item.id]:data.label}));}}catch(e){setError(e.message||'Could not suggest names.');}finally{setNaming(false);}}
 async function save(){if(!connected)return;setSaving(true);setError('');let count=0;const base=(apiUrl||API_BASE).replace(/\/$/,'');try{for(const item of items){const form=new FormData();form.append('file',item.blob,(names[item.id]||item.label)+'.png');form.append('label',names[item.id]||item.label);const r=await fetch(base+'/v1/stickers',{method:'POST',body:form,credentials:'include'});if(!r.ok){const body=await r.json().catch(()=>({}));throw new Error(body.detail||'Save failed ('+r.status+').');}count++;}setNotice?.(count+' stickers saved to your private collection.');items.forEach(x=>URL.revokeObjectURL(x.preview));setItems([]);setFile(null);onSaved?.();}catch(e){setError(count+' saved; '+e.message);onSaved?.();}finally{setSaving(false);}}
 return <section className="content-view sticker-studio-view"><div className="eyebrow"><span className="eyebrow-line"/> YOUR PRIVATE STICKER WORKSHOP</div><h1>Sticker Studio<span className="heading-period">.</span></h1><p className="subheading">Turn a sticker sheet into your own chat collection.</p>
 <div className="settings-card sticker-upload-card"><div className="sticker-studio-intro"><div className="feature-symbol"><Scissors size={22}/></div><div><span className="card-kicker">SHEET TO STICKERS</span><h2>Bring your sticker sheet</h2><p>Processing happens in this browser. Your original sheet is not uploaded.</p></div></div>
 <label className="sticker-dropzone"><ImagePlus size={28}/><strong>{file?file.name:'Choose a sticker sheet'}</strong><span>JPG, PNG or WebP · up to 15 MB</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>{setFile(e.target.files?.[0]||null);setItems([]);setError('');}}/></label>
 <label className="field-label">BACKGROUND SENSITIVITY · {tolerance}</label><input className="sticker-tolerance" type="range" min="8" max="90" value={tolerance} onChange={e=>setTolerance(Number(e.target.value))}/>
 <p className="field-help">The backdrop is estimated from many points around the image edge. Only background-coloured pixels connected to the outer edge are removed, helping preserve enclosed white details such as a bunny’s face or body. Start low; increase only if a halo remains.</p><button className="primary-button" onClick={process} disabled={!file||busy}>{busy?'Separating…':'Remove background & separate'}</button>{error&&<p className="sticker-error" role="alert">{error}</p>}</div>
 {items.length>0&&<div className="sticker-results"><div className="sticker-results-heading"><div><span className="card-kicker">REVIEW BEFORE SAVING</span><h2>{items.length} stickers detected</h2></div><div className="sticker-result-actions"><button className="secondary-button" onClick={suggestNames} disabled={naming}>{naming?'Naming…':'Suggest names'}</button><button className="secondary-button" onClick={()=>{items.forEach(x=>URL.revokeObjectURL(x.preview));setItems([]);}}>Clear all</button></div></div>
 <div className="sticker-results-grid">{items.map(item=><article className="sticker-result-card" key={item.id}><div className="sticker-result-preview"><img src={item.preview} alt={item.label}/></div><input aria-label={'Name for '+item.label} className="settings-input" value={names[item.id]||item.label} maxLength={100} onChange={e=>setNames(v=>({...v,[item.id]:e.target.value}))}/><button className="text-action danger-action" onClick={()=>{URL.revokeObjectURL(item.preview);setItems(v=>v.filter(x=>x.id!==item.id));}}><Trash2 size={13}/> Remove</button></article>)}</div>
 <button className="primary-button sticker-save-all" onClick={save} disabled={!connected||saving}>{saving?'Saving…':'Save '+items.length+' stickers to my collection'}</button>{!connected&&<p className="field-help">Sign in to your private SYLUS server before saving.</p>}</div>}
 <div className="small-note"><Star size={15}/> Nothing is added to chat until you favorite it.</div></section>;
}
