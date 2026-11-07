namespace rag;
using { cuid, managed } from '@sap/cds/common';

entity PolicyChunks : cuid, managed {
  source    : String(100);
  content   : LargeString @mandatory;
  embedding : LargeString;
}