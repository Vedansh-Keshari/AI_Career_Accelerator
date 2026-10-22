CFO INSIGHTS - WEBSITE (version 2)
Double-click index.html (works offline in any modern browser; no install, no server).
* Sample data is shown by default. Use the Dataset dropdown for "Sample 1 - cleaned" or "Sample 1 + 2 - synced".
* "Upload my own CSV" (top right): pick a messy CSV with the columns
    Invoice_ID, Client_name, Issue_date, Due_date, Amount(USD), Payment_status, Payment_date, Project_type, any_notes_or_remarks
  (only Invoice_ID, Client_name, Issue_date and Amount are required). Select several files at once to append and re-sync them.
  The file is cleaned inside your browser (nothing is uploaded anywhere) and every tab updates.
  Pick a sample in the Dataset menu to go back.
* Tabs: Dashboard, Invoices (search / filter / click headers to sort), Analytics, Overdue, Data quality, Ask your invoices.
* Ask your invoices: type a question (or pick one of 25 ready questions / 13 graphs). Answers, tables and graphs are worked out
  from the loaded data at the moment you ask; no API key or internet connection is needed. Try: "which client owes me the most",
  "invoices over $5,000", "details of INV-1020", "heatmap of clients by quarter". Follow-up chips appear under each answer.
* The yellow sticky note at the bottom shows notes and suggestions for whichever dataset is open.
Also included: CFO_Dashboard_Sample1.xlsx and CFO_Dashboard_Combined.xlsx and the raw messy CSVs in /data.
Dates like 03/11/2025 are read day-first (3 Nov). Overdue days are counted as of 22 Oct 2026.
