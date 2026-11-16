import React,{useState} from "react";
import {useQuery,useQueryClient} from "@tanstack/react-query";
import {ImagePlus,Sparkles} from "lucide-react";
import {getSylusImages} from "../endpoints/images/list_GET.schema";
import {postImageGenerate} from "../endpoints/images/generate_POST.schema";
import styles from "./SylusGalleryPanel.module.css";
export default function SylusGalleryPanel(){
 const qc=useQueryClient(),q=useQuery({queryKey:["sylus-gallery"],queryFn:getSylusImages});
 const [prompt,setPrompt]=useState("Standing beside his black car at night, one hand in his pocket, looking toward me with a faint amused expression."),[busy,setBusy]=useState(false),[error,setError]=useState("");
 async function generate(){setBusy(true);setError("");try{await postImageGenerate({prompt});await Promise.all([qc.invalidateQueries({queryKey:["sylus-gallery"]}),qc.invalidateQueries({queryKey:["sylus-main"]})])}catch(e){setError(e instanceof Error?e.message:"Could not generate the image.")}finally{setBusy(false)}}
 return <div className={styles.wrap}><section className={styles.create}><div className={styles.mark}><Sparkles size={18}/></div><div><p className={styles.eyebrow}>A PRIVATE IMAGE STUDIO</p><h2>Ask Sylus to show you a moment.</h2><p>Original game-style fan imagery, stored privately in your gallery and shared in the conversation.</p></div><textarea value={prompt} onChange={e=>setPrompt(e.target.value)} rows={3} placeholder="Describe the scene or what he is doing…"/><button onClick={generate} disabled={busy||prompt.trim().length<3}><ImagePlus size={16}/>{busy?"Creating your image…":"Generate a Sylus image"}</button>{error&&<p className={styles.error}>{error}</p>}<small>Free-tier integration when Cloudflare is connected · up to 3 generated images per day · no paid fallback.</small></section>
 <div className={styles.galleryHead}><h2>Your private gallery</h2><span>{q.data?.images.length??0} saved</span></div>
 {q.isLoading?<p className={styles.muted}>Opening your gallery…</p>:q.isError?<p className={styles.muted}>The gallery could not be loaded.</p>:!q.data?.images.length?<div className={styles.empty}>Your first image will appear here. Generated images are also added to the ongoing conversation.</div>:<div className={styles.grid}>{q.data.images.map(img=><article key={img.id}><a href={img.url} target="_blank" rel="noreferrer"><img src={img.url} alt="Generated Sylus scene"/></a><p>{img.prompt}</p><small>{new Date(img.createdAt).toLocaleString("en-GB",{timeZone:"Asia/Dhaka"})} · Bangladesh time</small></article>)}</div>}
 </div>;
}