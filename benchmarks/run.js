const fs = require('fs');
const { performance } = require('perf_hooks');

// TODO: replace this stub with your real translate() implementation.
async function translate(input) {
  // Example: require your engine here, e.g.:
  // const { translate } = require('../frontend/src/engine');
  // return translate(input);
  return { translation: input, method: 'stub' }; // placeholder
}

function median(a){ const b=[...a].sort((x,y)=>x-y); const n=b.length; return n? (n%2? b[(n-1)/2] : (b[n/2-1]+b[n/2])/2):0; }
function p95(a){ const b=[...a].sort((x,y)=>x-y); if(!b.length) return 0; const idx=Math.ceil(0.95*b.length)-1; return b[idx]; }

(async () => {
  const lines = fs.readFileSync('benchmarks/gold-set.jsonl','utf8').trim().split('\n');
  const gold = lines.map(JSON.parse);
  const results = { p_at_1:0, total:0, median_ms:0, p95_ms:0, by_category:{} };
  const latencies = [];

  for (const g of gold) {
    const t0 = performance.now();
    const r = await translate(g.input);
    const dt = performance.now() - t0;
    latencies.push(dt);

    const ok = (r.translation || '').toLowerCase().includes(g.expected.toLowerCase());
    results.total++;
    if (ok) results.p_at_1++;

    const cat = g.category;
    results.by_category[cat] = results.by_category[cat] || { total:0, correct:0 };
    results.by_category[cat].total++;
    if (ok) results.by_category[cat].correct++;
  }

  results.p_at_1 = results.p_at_1 / results.total;
  results.median_ms = median(latencies);
  results.p95_ms = p95(latencies);

  console.log(JSON.stringify(results, null, 2));
})();
