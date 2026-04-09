COPY personA FROM "node.csv" ;
COPY personB FROM "node.csv" ;
COPY personC FROM "node.csv" ;
COPY knows FROM "edge.csv" (from='personA', to='personB');
COPY knows FROM "edge.csv" (from='personA', to='personC');
COPY knows FROM "edge.csv" (from='personB', to='personC');
COPY likes FROM "edge.csv" (from='personA', to='personB');
COPY likes FROM "edge.csv" (from='personB', to='personA');
