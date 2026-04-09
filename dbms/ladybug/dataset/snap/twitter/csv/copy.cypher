COPY account FROM "twitter-nodes.csv";
COPY follows FROM "twitter-edges.csv" (DELIM=' ');
