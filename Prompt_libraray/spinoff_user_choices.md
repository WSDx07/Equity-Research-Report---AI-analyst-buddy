# Confirmed configuration ? November 11, 2026

The user selected fixed pass/fail thresholds and replaced the earlier relative-size factor with standalone spinoff market capitalization. The active `spinoff_factors.json` uses a 90-day window and 25 points each for market cap at or below USD 2 billion, post-distribution price decline at or above 15%, and insider ownership at or above 5%. Analyst coverage at or below two analysts has an intended weight of 25 but is set to zero because a verified source is not connected, as the user requested. Maximum active points are 75; no renormalization is specified. These cutoffs are provisional and do not prove the causes or investor alignment described in the user's rationale. Claims about exact book cutoffs remain unverified. The price reader and factors are not wired into a complete screen.

The earlier section below records the original user choices and historical examples; this update supersedes its factor and pending-scoring statements.

# Spinoff seeker: user choices and filing examples

Analysis date: 2026-11-10. These inputs are not a completed screen or a tested investment method.

## User-selected window and factors

Window: 90 calendar days after distribution. The existing prototype includes day 0 through day 90; this boundary is an implementation choice and must be explained in a report.

| Factor | Direction | Maximum weight | User-cited reading |
|---|---|---:|---|
| Spinoff market capitalization relative to former parent | Lower is higher ranked | 25 | Greenblatt, chapter 3 |
| Percentage decline from first regular-way close after distribution | Larger decline is higher ranked | 25 | Greenblatt, chapter 3; Klarman, chapter 10 |
| Insider equity ownership | Higher percentage is higher ranked | 25 | Greenblatt, chapter 3 |
| Sell-side analyst coverage | Fewer analysts is higher ranked | 25 | Greenblatt, chapter 3; Klarman, chapter 10 |

The user supplied the factors, directions, equal weights and window. The scoring method and input definitions are not yet specified. Do not invent thresholds or interpret insider ownership as insider open-market buying. The factor and window rationales are hypotheses; the cited books and claims about duration have not been independently verified here. Do not treat the scoring method as validated.

The existing `spinoff_factors.json` is a provisional example, uses different factors, and is not the user's final configuration. Do not treat it as the above choices.

## Positive filing example: Solventum

- The March 11, 2024 Form 10 amendment's [information statement](https://www.sec.gov/Archives/edgar/data/1964738/000162828024010270/exhibit991-form10x12ba2.htm) identifies 3M as parent, March 18, 2024 as the record date, and a ratio of one Solventum share for every four 3M shares. The April 1 date was expected and subject to conditions in that statement.
- 3M's [Form 8-K, Item 2.01](https://www.sec.gov/Archives/edgar/data/66740/000006674024000044/mmm-20240401.htm), filed April 4, 2024, reports completion on April 1, 2024.
- Under the prototype's inclusive 90-day boundary, the window ended June 30, 2024. This is a historical positive control; it is not within the 90-day window on November 10, 2026, and cannot meet the lab's current in-window positive-control requirement.

## Negative filing example: KKR FS Income Trust Select

- The February 2, 2024 [Form 10-12G](https://www.sec.gov/Archives/edgar/data/1975736/000119312524022590/d590653d1012g.htm), explanatory note, says the registrant filed voluntarily to permit an election to be regulated as a business development company. This supports treating it as a fund candidate, subject to checking later evidence before exclusion.
- A document's failure to mention a parent is not proof that none exists, and later distribution evidence could change a classification. This example has not yet been tested through the live seeker.

## Pending

On November 11, 2026, the user proposed fixed-threshold scoring and provisional cutoffs of USD 2 billion for absolute market capitalization, 15% price decline, 5% insider ownership, and two analysts. The absolute-size proposal differs from the previously selected size relative to the parent. The user was asked which size factor to use and whether to adopt the other three provisional cutoffs. Await those answers before updating the active configuration. The stated claims about typical cohort size and specific book cutoffs have not been verified. For each factor, obtain a supported data source and define the dates, denominator or covered population, and any missing-data handling before implementation. The existing prototype has not been validated on these examples. The user requested the price reader later; do not implement or run it in this session unless the user changes that request.
