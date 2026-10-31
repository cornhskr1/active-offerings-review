# NBB result-row recovery

The published October 30 schedule audit reported `NBB fixture identity or pairing changed`. A single successful, guarded HTTP request to the configured official schedule URL returned 153 rows for 2026/27. The first 33 had numeric scores and same-edition publisher result articles instead of the upcoming-game detail links expected by the adapter. One such row caused the entire parser to fail.

Evidence URL: https://lnb.com.br/nbb/tabela-de-jogos

The repair validates IDs, named opponents, kickoff, season, and duplicate identities before distinguishing result rows. A result requires two numeric scores, consistent repeated result anchors, and a same-publisher HTTPS article path for the current edition. It is never emitted as upcoming. Rows without results still require their exact-edition fixture detail link. An incomplete inventory, malformed result, contradictory duplicate, changed identity, or external link fails the whole source. Minimum inventory checks include validated results, so finishing games does not progressively invalidate an otherwise valid remaining schedule.

The fetch helper now returns response bytes so the HTML parser honors the publisher's UTF-8 declaration. The previous default Latin-1 decoding corrupted names such as União and São José. Request routes, access holds, header negotiation and timeouts are unchanged.

Offline replay of the fetched payload through the actual collector branch retained 120 unplayed fixtures, with 13 in the October 30–November 6 Central Time review window and no errors. The last available unplayed fixture in this response is December 29, 2026. This establishes neither full-season nor playoff completeness, age eligibility, nor wagering approval. No normal scheduled collector was manually triggered, and no production coverage increase is claimed before a normal publication.

The regression fixture contains a trimmed factual result row plus 20 upcoming rows from the same response, including accented names. Tests cover remaining schedules below 20 upcoming games, malformed scores, conflicting result copies, duplicate IDs, dates, edition/link changes, exact catalog scope, and the retained minimum inventory guard. Existing publisher access and API quota tests remain in the full suite.

Release the app change before its companion data-repository trusted-code manifest update. Both require owner approval. Observe a normal scheduled publication afterward; source blocks remain explicit until then.
