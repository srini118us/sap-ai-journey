import cds from '@sap/cds';

const DIM = 16;
function embed(text) {
  const v = new Array(DIM).fill(0);
  const t = (text || '').toLowerCase();
  for (let i = 0; i < t.length; i++) v[t.charCodeAt(i) % DIM] += 1;
  const norm = Math.sqrt(v.reduce((s, x) => s + x * x, 0)) || 1;
  return v.map(x => x / norm);
}

export default class RagService extends cds.ApplicationService {
  init() {
    this.on('reindex', async () => {
      const rows = await SELECT.from('rag.PolicyChunks');
      for (const r of rows) {
        await UPDATE('rag.PolicyChunks').set({ embedding: embed(r.content) }).where({ ID: r.ID });
      }
      return `${rows.length} chunks indexed`;
    });

    this.on('search', async (req) => {
      const { query, topK = 3 } = req.data;
      const vec = JSON.stringify(embed(query));
      const rows = await cds.run(
        `SELECT content AS "content",
                COSINE_SIMILARITY(embedding, TO_REAL_VECTOR(?)) AS "score"
         FROM rag_PolicyChunks
         ORDER BY "score" DESC
         LIMIT ?`, [vec, topK]);
      return rows.map(r => ({
        content: Buffer.isBuffer(r.content) ? r.content.toString('utf8') : r.content,
        score: r.score
     }));
    });
     return super.init();
  }
}
