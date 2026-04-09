load extension "extension/json/build/libjson.lbug_extension";
copy person from "vPerson.json";
copy person from "vPerson2.json" (format="unstructured")
copy organisation from "vOrganisation.json";
copy movies from "vMovies.json";
copy knows from "eKnows.json";
copy knows from "eKnows_2.json";
copy studyAt from "eStudyAt.json";
copy workAt from "eWorkAt.json";
copy meets from "eMeets.json";
copy marries from "eMarries.json";
