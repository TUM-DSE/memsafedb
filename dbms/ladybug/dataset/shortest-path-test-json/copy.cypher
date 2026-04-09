load extension "extension/json/build/libjson.lbug_extension";
COPY person FROM "vPerson.json" (format='array', sample_size=1, maximum_depth=10);
COPY knows FROM "eKnows.json";
