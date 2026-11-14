# Equity research data desk prompt

## Original prompt

Build the data side of an equity-research desk in Python, modeled on Section 3.1 of Francis & Zhang (2026); the model roles come later. Read my SEC User-Agent as SEC_USER_AGENT from the .env file in this folder and send it on every request. The program takes a ticker as its argument, an optional --peers list of tickers, an optional --price number, and an optional --step number to run one step only. Nothing in the code names a company. Seven steps, each printed as it runs: (1) resolve the ticker to its CIK from SEC's company_tickers.json; (2) list the company's filings from the EDGAR submissions API and pick the latest 10-K, the latest 10-Q, and the latest 8-K whose document reports Item 2.02, the earnings release, printing each one's accession number and the "Accepted" time shown on its EDGAR index page; (3) download the three documents, the 8-K's Exhibit 99.1 for the release, convert each to plain text and save them in a folder named by company, date and time of the run; (4) fetch the XBRL company facts and, for the latest fiscal year, print total revenue, operating income, net income, diluted EPS, stockholders' equity, long-term debt and its current portion, cash from operations and additions to property and equipment, each with its tag, period end and filing, choosing among a concept's candidate tags the one whose latest year is newest and reading every concept for the same fiscal year as revenue, with the prior year beside it; (5) a calculator, in code, that prints with its arithmetic revenue growth, operating margin, return on average equity, debt to equity with the current portion included, free cash flow as cash from operations minus additions to property and equipment, and P/E from --price; (6) from the release text, print the lines that state the quarter's total revenue and diluted EPS; (7) for each peer, the same facts and the operating margin on the same definition. Save the facts beside the texts. When you finish, tell me the exact command to install any packages it needs and the exact command to run it on a ticker with peers and a price.

## Improved prompt

Build the data side of an equity research desk in Python. Use Section 3.1 of Francis and Zhang (2026) as the model for the workflow. I will add the model roles later.

Read the SEC User-Agent value from `SEC_USER_AGENT` in the `.env` file in this folder. Send that value with every request. Do not put a company name in the code.

The program must take a ticker as an argument. It must also accept:

- `--peers`: an optional list of peer tickers
- `--price`: an optional stock price
- `--step`: an optional step number; when given, run only that step

Run these seven steps in order. Print the step number and its result as each step runs.

1. Resolve the ticker to its CIK with SEC `company_tickers.json`.
2. Get the company’s filing list from the EDGAR submissions API. Select the latest 10-K, the latest 10-Q, and the latest 8-K whose document reports Item 2.02, “Results of Operations and Financial Condition.” For each filing, print its accession number and the **Accepted** time shown on its EDGAR index page.
3. Download the three filing documents and Exhibit 99.1 from the selected 8-K. Convert each document to plain text. Save the text files in a folder whose name contains the company name and the date and time of the run.
4. Get the company’s XBRL company facts. For the latest fiscal year, print total revenue, operating income, net income, diluted EPS, stockholders’ equity, long-term debt, the current portion of long-term debt, cash from operations, and additions to property and equipment. For each fact, print its XBRL tag, period end, and filing. If a concept has more than one candidate tag, choose the tag whose latest available fiscal year is newest. Use the fiscal year selected for revenue for every other concept. Print the prior fiscal year’s value beside each current-year value.
5. Use a calculator in the code. Print each result and the arithmetic used to calculate it: revenue growth, operating margin, return on average equity, debt to equity including the current portion of debt, free cash flow as cash from operations minus additions to property and equipment, and P/E using `--price`.
6. From the earnings release text, print the lines that state the quarter’s total revenue and diluted EPS.
7. For each ticker in `--peers`, print the same facts and calculate operating margin with the same definition used in step 5.

Save the facts in the same folder as the text files. When the program is complete, give me the exact command to install any required packages and the exact command to run it with a ticker, peers, and a price.
