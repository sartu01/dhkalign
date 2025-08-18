const fs = require('fs'), path = require('path');
const infile = process.argv[2] || 'inbox/CLAUDE_DUMP.txt';
if (!fs.existsSync(infile)) { console.error('Missing', infile); process.exit(1); }
const DRY = process.env.DRY_RUN === '1';
const src = fs.readFileSync(infile,'utf8');
const parts = src.split(/```/g);
let wrote = 0, skipped = 0;

for (let i=1; i<parts.length; i+=2) {
  const headerPlusCode = parts[i].split('\n');
  let dest = null, startIdx = 0;
  for (let j=0; j<Math.min(5, headerPlusCode.length); j++) {
    const line = headerPlusCode[j].trim();
    const m = line.match(/(?:^|^#|^\/\/|^\/\*)\s*path:\s*([A-Za-z0-9_\-./]+)\s*/i);
    if (m) { dest = m[1]; startIdx = j+1; break; }
  }
  if (!dest) { skipped++; continue; }
  if (/^data\/releases\//.test(dest)) { console.error('Refusing to touch', dest); skipped++; continue; }
  const out = headerPlusCode.slice(startIdx).join('\n').replace(/\s+$/,'') + '\n';
  const target = path.normalize(dest);
  if (DRY) { console.log('WILL WRITE', target); continue; }
  fs.mkdirSync(path.dirname(target), { recursive:true });
  fs.writeFileSync(target, out, 'utf8');
  console.log('WROTE', target);
  wrote++;
}
console.log(`Done. wrote=${wrote} skipped=${skipped} dry_run=${DRY}`);
