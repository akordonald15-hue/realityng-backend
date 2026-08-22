# RealityNG Financial Product Boundaries

Status: Sprint 16 working baseline, 2026-08. **REQUIRES PROFESSIONAL REVIEW**.

## Platform role

RealityNG is a marketplace, workflow orchestrator, communication layer, record and notification system, and partner-integration platform. It is not a lender, underwriter, bank, credit bureau, escrow custodian, investment platform, insurer, or legal adviser.

## Escrow boundary

RealityNG may record and display partner-reported escrow statuses and events and receive authenticated partner updates. RealityNG does not hold funds, control partner bank accounts, guarantee funding, release, transaction completion, refunds, or counterparty performance. The external escrow provider owns custody, settlement instructions, and regulated obligations. Live providers are disabled by `ESCROW_LIVE_ACTIVATION_ENABLED=False` until documented approval.

Responsible parties: provider for custody and provider events; transaction parties for instructions and agreements; RealityNG for access control, faithful record display, audit logs, and incident routing. **REQUIRES PROFESSIONAL REVIEW**.

## Financing boundary

RealityNG may collect application data and documents, record explicit versioned consent, forward approved data, and display partner responses. The financing partner alone approves, rejects, underwrites, prices, performs any credit assessment, contracts with applicants, disburses funds, and collects repayments. RealityNG does not promise eligibility, approval, rates, timing, or funding. Partner submission is disabled by `FINANCING_LIVE_ACTIVATION_ENABLED=False` until documented approval.

## Activation conditions

Neither live capability may be enabled until legal, privacy, financial-services, partner-contract, security, operational-owner, incident-response, and user-disclosure approvals are documented in the professional approval matrix. Configuration changes must be reviewed, tested, logged, and independently approved. **REQUIRES PROFESSIONAL REVIEW**.

