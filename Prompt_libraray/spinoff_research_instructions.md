# Spinoff seeker: reading, factors, and filing checks

You need to produce three things:

1. A list of factors and a window length.
2. One SEC filing for a real spinoff.
3. One Form 10 filing for a company or fund that is not a spinoff.

The course asks you to write your factor list by hand. You can use paper or a notes app to collect the filing details.

## Part 1: Read and choose your factors

### Step 1: Get the reading

1. Go to [Purdue Libraries](https://lib.purdue.edu/).
2. Search for *You Can Be a Stock Market Genius* by Joel Greenblatt.
3. Open or borrow the book through the library.
4. Read Chapter 3, which covers spinoffs.

The course also assigns the spinoff pages in Chapter 10 of Seth Klarman's *Margin of Safety*. If you cannot get that book in time, the course says Greenblatt's chapter is enough for this week.

### Step 2: Write one sentence about the reading

On paper, answer this question in your own words:

> Why might some people sell shares of a spinoff soon after they receive them?

You do not need to use financial terms. Explain the idea as you understand it.

### Step 3: Choose what the seeker should look for

A **factor** is a condition you want the seeker to use when it ranks companies.

The course gives these examples:

| Possible factor | What it means | Example direction |
|---|---|---|
| Size relative to parent | How large the new company is compared with its former parent | Smaller ranks higher |
| Weak share price | How much the new company's share price has fallen | A larger fall ranks higher |
| Analyst coverage | How many analysts follow the company | Fewer analysts rank higher |
| Insider buying | Whether company insiders bought shares | More buying ranks higher |
| Company size | How large the new company is on its own | Smaller ranks higher |

These are examples, not a list you must use. Pick the factors that make sense to you after the reading. You do not have to use all five.

### Step 4: Write your list

For each factor you choose, write:

1. **Factor:** What do you want to check?
2. **Direction:** Should a higher or lower value get more points?
3. **Weight:** How many points can it get?
4. **Reading:** Which book and chapter gave you the idea?

Here is a practice example to show the format. It is not a recommendation or a list you need to copy:

```text
Factor: Company size
Direction: Smaller companies get more points
Weight: 10 points
Reading: Greenblatt, Chapter 3
```

A weight controls how much a factor affects the rank. For example, a 20-point factor can have twice the effect of a 10-point factor, if each factor is scored as a fixed number of points.

### Step 5: Choose a window

Write this on the same page:

```text
Window: _____ days after the distribution date
```

You can choose 90 days, 365 days, or another number. You can change it later. The window controls which companies are eligible for the current ranking. It is separate from the start date used to search for distributions.

### Step 6: Send me your choices

Type your list here when you are ready. I can then put your choices into the seeker's configuration file.

## Part 2: Find one real spinoff

You will use the SEC's EDGAR search page. EDGAR is the SEC's public collection of company filings.

### Step 1: Open the search page

1. Go to [SEC EDGAR Full Text Search](https://www.sec.gov/edgar/search/).
2. Search for:

   ```text
   "information statement"
   ```

3. Use the filing-date filter to look at approximately the past year.
4. If the form filter is available, select **10-12B**, **10-12G**, or their amendments.

The SEC search lets you search filing text and filter the results. See [SEC: Search Filings](https://www.sec.gov/search-filings).

### Step 2: Open a possible result

1. Open a result with form type **10-12B**, **10-12G**, **10-12B/A**, or **10-12G/A**.
2. Look for a document or exhibit called **Information Statement**.
3. Open it.

A Form 10 alone does not prove that the company is a spinoff. You need to read what the document says.

### Step 3: Check that it is a spinoff

Near the start of the information statement, look for a sentence that says a parent company will distribute shares of another business to its shareholders.

For this exercise:

- The **parent** is the company giving out the shares.
- The **new company** is the business being separated.
- The **distribution** is the transfer of the new company's shares to the parent's shareholders.

Do not use the example if the filing says the distribution is only proposed and you cannot confirm it happened. Look for a later filing, such as the parent's Form 8-K, that confirms completion.

### Step 4: Find the dates and ratio

In the information statement, use **Ctrl + F** to search for:

```text
distribution date
```

Then search for:

```text
record date
```

Then search for:

```text
distribution ratio
```

The ratio might be written in a sentence instead of under that exact label. For example, it might say that shareholders receive one new share for a stated number of parent-company shares.

If you cannot find a fact, write **?not found?**. Do not guess.

### Step 5: Write down the answer

Copy this template into your notes and fill in what you can:

```text
REAL SPINOFF

New company:
Parent company:
Form type:
Filing date:
Record date:
Distribution date:
Distribution ratio:
Section or page where I found the facts:
Link to the information statement:
Link to the filing that confirms the distribution happened:
```

**Check:** The filing date and distribution date are different things. The filing date is when a document was submitted to the SEC. The distribution date is when the shares were distributed.

The lab asks for a recent spinoff and a filing that your partner can use to check the parent and dates.

## Part 3: Find one Form 10 filer that is not a spinoff

### Step 1: Return to EDGAR

1. Go back to [SEC EDGAR Full Text Search](https://www.sec.gov/edgar/search/).
2. Search for:

   ```text
   "investment company"
   ```

3. If available, filter the form type to **10-12G** or **10-12G/A**.
4. Open a result.

### Step 2: Read enough to establish what it is

Look for a sentence that identifies the registrant as a fund or an investment company.

Then check whether the filing also describes a parent distributing the business to its shareholders. If it does, the case may be more complicated: choose another example or send me the filing to review with you.

Do not conclude that a company is not a spinoff only because you could not find the words ?information statement.? For your answer check, a filing that clearly identifies the registrant as a fund is easier to explain.

### Step 3: Write down the answer

```text
NOT A SPINOFF

Company or fund name:
Form type:
Filing date:
Why I think it is not a spinoff:
Section or page that supports the reason:
Link to the filing:
```

## What to send me

When you have them, send me:

1. Your factor choices, directions, weights, and window length.
2. The link and notes for your spinoff example.
3. The link and notes for your non-spinoff example.

You can send them one at a time. If you get stuck on an EDGAR result, send me its link and tell me which step you reached.

## Course sources

- [Week 4 ? The Investor's Desk: Books Become Skills](../Lab%20docx/Week%204%20%E2%80%94%20The%20Investor's%20Desk_%20Books%20Become%20Skills%20%C2%B7%20FIN%2067110.pdf)
- [Lab 06 ? The Seeker](../Lab%20docx/Lab%2006%20%E2%80%94%20The%20Seeker%20%C2%B7%20FIN%2067110.pdf)
