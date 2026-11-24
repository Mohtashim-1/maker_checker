# Maker Checker

Approval workflows for ERPNext transactional documents:

- Sales Invoice, Payment Entry, Journal Entry, Sales Order, Delivery Note, Payment Request
- Purchase Invoice, Purchase Order, Purchase Receipt
- Stock Entry
- Expense Claim (when HRMS is installed)

## Roles

| Role | Can |
|---|---|
| Document Maker | Create / edit Draft documents, submit for approval |
| Document Checker | Approve (submit) or reject back to Draft |

## Flow

`Draft` → **Submit for Approval** → `Pending Approval` → **Approve** → `Approved` (docstatus 1)  
`Pending Approval` → **Reject** → `Draft` (rejection reason required on document if field exists; otherwise comment)

## Install

```bash
bench --site dantata.codecrestsolutions.com install-app maker_checker
```
