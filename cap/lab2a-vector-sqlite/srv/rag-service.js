import cds from '@sap/cds';

const DIM = 16;
function embed(text) {
  const v = new Array(DIM).fill(0);
  const t = (text || '').toLowerCase();
  for (let i = 0; i < t.length; i++) v[t.charCodeAt(i) % DIM] += 1;
  const norm = Math.sqrt(v.reduce((s, x) => s + x * x, 0)) || 1;
  return v.map(x => x / norm);
}
function dot(a, b) {
  let d = 0;
  for (let i = 0; i < a.length; i++) d += a[i] * b[i];
  return d;
}

export default class RagService extends cds.ApplicationService {
  init() {
    const { PolicyChunks } = this.entities;

    this.on('reindex', async () => {
      const rows = await SELECT.from(PolicyChunks);
      for (const r of rows) {
        await UPDATE(PolicyChunks).set({ embedding: JSON.stringify(embed(r.content)) }).where({ ID: r.ID });
      }
      return `${rows.length} chunks indexed`;
    });

    this.on('search', async (req) => {
      const { query, topK = 3 } = req.data;
      const q = embed(query);
      const rows = await SELECT.from(PolicyChunks).where({ embedding: { '!=': null } });
      return rows
        .map(r => ({ content: r.content, score: dot(q, JSON.parse(r.embedding)) }))
        .sort((a, b) => b.score - a.score)
        .slice(0, topK);
    });

    return super.init();
  }
}