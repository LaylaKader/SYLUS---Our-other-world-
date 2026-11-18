# Single-container image for Render and other Docker web hosts.
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json ./package.json
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN apt-get update && apt-get install -y --no-install-recommends unzip && rm -rf /var/lib/apt/lists/*
RUN mkdir -p public/stickers/assets && unzip -q public/stickers/sylus-49-stickers-transparent.zip -d /tmp/sylus-stickers && find /tmp/sylus-stickers -type f -iname '*.png' -print0 | xargs -0 -I{} cp {} public/stickers/assets/ && node -e "const fs=require('fs');const p='public/stickers/assets';const files=fs.readdirSync(p).filter(x=>/\\.png$/i.test(x)).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));const labels=['Love you','That’s all?','Good night','What are you doing?','Surprised!','Hmm…','No','Your Majesty','So comfy','Oh, dear','Nope','You’re the best','Hello, little one','A little sparkle','Cheers!','Thinking','Looking good','Look at me','So tired','Too tired to care','Huh?','What?','Fired up','All mine','So annoying'];const items=files.map((f,i)=>({id:'sylus-'+String(i+1).padStart(2,'0'),label:labels[i]||('Sticker '+(i+1)),src:'/stickers/assets/'+encodeURIComponent(f)}));fs.writeFileSync('public/stickers/manifest.json',JSON.stringify(items));if(files.length!==49)console.log('Sticker archive contains '+files.length+' PNG files (expected 49).');"
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST_DIR=/srv/frontend

WORKDIR /srv/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY character /srv/character
COPY --from=frontend-build /build/frontend/dist /srv/frontend

EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips=*"]
