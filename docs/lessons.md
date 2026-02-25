# Lessons Learned

- Never assume primary key uniqueness from code format alone — validate against real data before committing to a PK strategy. DUN codes repeat across states. (Sprint 0.1)
- Always test CSV/Excel import with real data files early, not just test fixtures. Encoding, column format, and value format surprises only surface with real data. (Sprint 0.1)
- Malaysian government data files often use cp1252 encoding, not UTF-8. Try cp1252 first for .csv files from government sources. (Sprint 0.1)
