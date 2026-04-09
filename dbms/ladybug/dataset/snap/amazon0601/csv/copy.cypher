COPY account FROM "amazon-nodes.csv";
COPY follows FROM "amazon-edges.csv" (DELIM="\\t");
