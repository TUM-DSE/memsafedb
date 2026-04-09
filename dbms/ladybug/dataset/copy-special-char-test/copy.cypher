COPY person FROM "vPerson.csv" (ESCAPE = "#", QUOTE = "-");
COPY organisation FROM "vOrganisation.csv" (ESCAPE = "#", QUOTE = "=");
COPY workAt FROM "eWorkAt.csv" (ESCAPE = "#", QUOTE = "=");
