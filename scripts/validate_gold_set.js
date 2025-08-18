const fs = require('fs');
const path = 'benchmarks/gold-set.jsonl';
const lines = fs.readFileSync(path,'utf8').trim().split('\n');

const enums = {
  category: new Set(['sarcasm','dialect','grammar','slang','safety']),
  dialect: new Set(['standard','sylheti','chittagonian','other']),
  difficulty: new Set(['easy','med','hard']),
};

let errors = [];
lines.forEach((line, i) => {
  let o;
  try { o = JSON.parse(line); }
  catch(e){ errors.push(`Line ${i+1}: invalid JSON`); return; }

  const need = ['input','expected','category','dialect','difficulty','notes'];
  for (const k of need) if (!(k in o)) errors.push(`Line ${i+1}: missing field '${k}'`);

  if (o.category && !enums.category.has(o.category)) errors.push(`Line ${i+1}: bad category '${o.category}'`);
  if (o.dialect && !enums.dialect.has(o.dialect)) errors.push(`Line ${i+1}: bad dialect '${o.dialect}'`);
  if (o.difficulty && !enums.difficulty.has(o.difficulty)) errors.push(`Line ${i+1}: bad difficulty '${o.difficulty}'`);

  if (typeof o.input !== 'string' || !o.input.trim()) errors.push(`Line ${i+1}: empty input`);
  if (typeof o.expected !== 'string' || !o.expected.trim()) errors.push(`Line ${i+1}: empty expected`);
});

if (errors.length) {
  console.error(`VALIDATION FAILED (${errors.length} issues):`);
  errors.slice(0, 50).forEach(e => console.error(' -', e));
  if (errors.length > 50) console.error(` ...and ${errors.length-50} more`);
  process.exit(1);
} else {
  console.log(`VALIDATION OK: ${lines.length} items`);
}
