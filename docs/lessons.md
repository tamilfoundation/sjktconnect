# Lessons Learned

- Never assume primary key uniqueness from code format alone — validate against real data before committing to a PK strategy. DUN codes repeat across states. (Sprint 0.1)
- Always test CSV/Excel import with real data files early, not just test fixtures. Encoding, column format, and value format surprises only surface with real data. (Sprint 0.1)
- Malaysian government data files often use cp1252 encoding, not UTF-8. Try cp1252 first for .csv files from government sources. (Sprint 0.1)
- parlimen.gov.my has an invalid SSL certificate. Use `verify=False` when downloading from this domain. (Sprint 0.2)
- Not every parliamentary sitting mentions Tamil schools. The Jan-Mar 2026 session had only 2/15 sittings with mentions. Budget debates (Oct-Nov) are more likely to contain school mentions. (Sprint 0.2)
- When using `unittest.mock.patch` on Windows with deep module paths (e.g. management commands), `patch.object()` on the imported module is more reliable than patching by string path. (Sprint 0.2)
- Two Python versions on this machine (3.11 and 3.13). Tests run on 3.11. Always install packages using the correct Python executable, not just `pip`. (Sprint 0.2)
- When extracting named entities from text with regex, don't hard-limit word counts — use semantic boundaries (stop words, known delimiters) or progressive shortening against a known dictionary. Fixed word limits silently reject valid matches. (Sprint 0.3)
