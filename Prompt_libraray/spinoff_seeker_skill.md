# Task: Spinoff Seeker Agent Skill

Create an agent skill in the directory where the coding agent reads skills. Name the skill for its search objective.

The skill must find U.S. spinoffs on SEC EDGAR that have a distribution date on or after a user-specified start date.

### 1. Data Collection and Rate Limits
- Read the SEC EDGAR form indexes for:
  - Form 10 registration statements and their amendments.
  - Stock exchange CERT filings.
  - Form 8-K filings submitted at the time of distribution.
- Read each filing folder on EDGAR to extract the required facts.
- Include the SEC `User-Agent` from `.env` in every HTTP request.
- Keep the request rate below the maximum rate that EDGAR permits.

### 2. Fact Registry
- Maintain a registry file of established facts extracted from filings:
  - Parent company.
  - Distribution ratio.
  - Record date.
  - Distribution date.
  - Source filing and source section for each fact.
- Populate the registry only with facts found in readable filings.
- If a fact cannot be found, leave the field blank and state this condition in the report.
- Do not estimate any fact.

### 3. Registrant Filtering
- Drop a registrant if it is not a spinoff, and record the reason and source filing:
  - Drop a Form 10 with no Information Statement.
  - Drop an investment fund.
  - Drop a company that registers shares it already holds.
  - **Exception:** Do not drop the registrant if a later filing shows that a parent company distributes the business.

### 4. Lifecycle Stages
Assign each entity one of five stages:
1. `registered`
2. `listing approved`
3. `trading`
4. `in its window`
5. `past it`

- Because the distribution Form 8-K often belongs to the parent company, read the parent company filings by using the parent CIK from the registry.
- A Form 10-Q, Form 10-K, or Form 4 in the new company's filing list confirms that the new company trades.

### 5. Pricing
- Obtain closing prices from the user's closes reader.
- Set the first price to the first closing price after the distribution date.
- Never use a when-issued price.
- Print the price date beside every price.

### 6. Ranking and Window Evaluation
- Read a configuration file provided by the user. The file defines:
  - The window length in days after the distribution date.
  - The ranking factors, each with its assigned weight and direction.
- Rank entities that are in their window.
- Print the points per factor for each ranked entity.
- If an entity lacks a required date, list the entity as unranked and state the reason.

### 7. Report Requirements
Write a report saved with its run date and timestamp. The report must contain:
- **First line:** Run date, price date, and index date.
- **Section 1:** Names in their window, sorted by rank.
- **Section 2:** Watch list of registered names that do not trade yet.
- **Section 3:** Dropped registrants with associated reasons.
- **Section 4:** Explicit statements of what the data cannot show.
- **Final line:** Exactly `"screens, not recommendations"`.

### 8. Code and Test Standards
- Do not include any company names in the code.
- Write unit tests using synthetic (made-up) data for every rule.
- Change a rule only after its corresponding test changes.
- Provide the exact shell command to execute the seeker with a start date.
- Provide the exact shell command to run all tests.
