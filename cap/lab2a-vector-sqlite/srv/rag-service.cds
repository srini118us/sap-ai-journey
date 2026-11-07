using rag from '../db/schema';

service RagService @(path: '/odata/v4/rag') {
  entity PolicyChunks as projection on rag.PolicyChunks;

  function reindex() returns String;
  function search(query: String, topK: Integer) returns array of {
    content : String;
    score   : Double;
  };
}