-- ============================================================
-- ComplianceOS — Threshold Rules Seed Data
-- The complete deterministic compliance rule engine.
-- Every row = one compliance obligation trigger.
-- Source citations are real Indian regulatory references.
-- ============================================================

-- ============================================================
-- GST RULES
-- ============================================================

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-001-v1', 'GST-001', 1,
    'GST', 'Registration',
    'GST Registration Required (Services)',
    'Your business provides services and annual aggregate turnover has exceeded ₹20 Lakh. GST registration is mandatory within 30 days of crossing this threshold. Operating without GSTIN attracts penalties equal to 100% of tax due or ₹10,000 — whichever is higher.',
    'annual_turnover_cr', '>=', '0.20', 'numeric',
    'has_gstin', '==', '0', 'boolean',
    'HIGH', 'One-time', 30, 25000,
    'Higher of ₹10,000 or 100% of tax evaded',
    '["Obtain PAN of business entity", "Gather proof of business address", "Register on GST Portal at gst.gov.in", "Complete ARN verification within 3 working days", "Display GSTIN on all invoices and signboards"]',
    'CGST Act 2017, Section 22(1)', 'https://gst.gov.in',
    '2017-07-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-002-v1', 'GST-002', 1,
    'GST', 'Registration',
    'GST Registration Required (Goods)',
    'Your business deals in goods and annual aggregate turnover has exceeded ₹40 Lakh. GST registration is mandatory. Special category states have a lower threshold of ₹20 Lakh.',
    'annual_turnover_cr', '>=', '0.40', 'numeric',
    'has_gstin', '==', '0', 'boolean',
    'HIGH', 'One-time', 30, 25000,
    'Higher of ₹10,000 or 100% of tax evaded',
    '["Obtain PAN of business entity", "Gather proof of business address and bank statement", "Register on GST Portal at gst.gov.in", "Complete ARN verification within 3 working days", "Display GSTIN on all invoices"]',
    'CGST Act 2017, Section 22(1)', 'https://gst.gov.in',
    '2019-04-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-003-v1', 'GST-003', 1,
    'GST', 'E-Invoicing',
    'Mandatory E-Invoicing (B2B Transactions)',
    'Your annual aggregate turnover exceeds ₹5 Crore. All B2B invoices must be registered on the Invoice Registration Portal (IRP) before being issued to buyers. The IRP generates a unique IRN and QR code that must appear on every B2B invoice. Buyers cannot claim ITC without a valid IRN.',
    'annual_turnover_cr', '>=', '5.0', 'numeric',
    'b2b_sales_pct', '>', '0', 'numeric',
    'HIGH', 'Continuous', 0, 50000,
    '₹10,000 per invoice or 100% of tax amount — whichever is higher. Additionally, buyer loses ITC which creates commercial disputes.',
    '["Register on IRP portal at einvoice1.gst.gov.in", "Integrate your billing/ERP software with IRP API (or use GSP)", "Test with 1-2 sample invoices before going live", "Configure auto-IRN generation for all B2B invoices", "Archive all IRNs for minimum 8 years", "Brief your accounts team on the new process"]',
    'CBIC Notification No. 17/2022-Central Tax dated 01-08-2023', 'https://einvoice1.gst.gov.in',
    '2023-08-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-004-v1', 'GST-004', 1,
    'GST', 'Filing',
    'Monthly GST Filing Required (GSTR-1 and GSTR-3B)',
    'Your annual aggregate turnover exceeds ₹5 Crore. You cannot use the QRMP (Quarterly Return Monthly Payment) scheme. You must file GSTR-1 by the 11th and GSTR-3B by the 20th of every month — 24 returns per year instead of 8 under QRMP.',
    'annual_turnover_cr', '>', '5.0', 'numeric',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Monthly', 0, 10000,
    '₹50 per day late fee for GSTR-3B (₹20 for nil return). ₹50 per day for GSTR-1. Max ₹5,000-10,000 per return. Plus 18% p.a. interest on unpaid tax.',
    '["Set calendar reminders: GSTR-1 due 11th, GSTR-3B due 20th of every month", "Ensure your accountant/CA is briefed on monthly schedule", "Reconcile sales data by 5th of each month", "Reconcile ITC from GSTR-2B before filing GSTR-3B", "Set up auto-payment of tax to avoid interest"]',
    'CGST Act 2017, Section 37 and 39; CGST Rules 61 and 59', 'https://gst.gov.in',
    '2023-08-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-005-v1', 'GST-005', 1,
    'GST', 'Filing',
    'QRMP Scheme Available (Quarterly Filing)',
    'Your annual aggregate turnover is ₹5 Crore or below. You are eligible for the QRMP scheme — file GSTR-1 and GSTR-3B quarterly (4 times/year) while paying tax monthly via PMT-06 challan. This significantly reduces compliance burden.',
    'annual_turnover_cr', '<=', '5.0', 'numeric',
    NULL, NULL, NULL, NULL,
    'MEDIUM', 'Optional', 0, 0,
    'No penalty — this is a beneficial scheme. Not opting in means you must file monthly.',
    '["Log in to GST Portal at gst.gov.in", "Go to Services > Returns > Opt-in for QRMP", "Select opt-in before end of the quarter to apply from next quarter", "Set up monthly PMT-06 payment reminders", "Quarterly filing deadlines: GSTR-1 by 13th, GSTR-3B by 22nd-24th"]',
    'CGST Rule 61A; CBIC Circular No. 143/13/2020', 'https://gst.gov.in',
    '2021-01-01', NULL, 1, 0, 1,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-006-v1', 'GST-006', 1,
    'GST', 'Audit',
    'Annual GST Audit — GSTR-9C Required',
    'Your annual aggregate turnover exceeds ₹5 Crore. You must file GSTR-9C (Annual Reconciliation Statement) certified by a Chartered Accountant or Cost and Management Accountant. Due date is 31st December after the financial year end. Failure to file attracts ₹200 per day penalty.',
    'annual_turnover_cr', '>=', '5.0', 'numeric',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Annual', 273, 100000,
    '₹200 per day late fee, subject to maximum 0.5% of annual turnover',
    '["Engage a CA/CMA for GSTR-9C certification by September", "Complete books of accounts reconciliation for the full year", "Reconcile GSTR-1 vs GSTR-3B vs books", "Reconcile ITC claimed vs ITC available in GSTR-2A/2B", "File GSTR-9 (Annual Return) first, then GSTR-9C", "Deadline: 31st December after FY end"]',
    'CGST Act 2017, Section 35(5) and 44; CGST Rule 80', 'https://gst.gov.in',
    '2018-07-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-007-v1', 'GST-007', 1,
    'GST', 'E-Way Bill',
    'E-Way Bill Required for Goods Movement',
    'If your business moves goods worth more than ₹50,000 (₹1 Lakh for intra-state in some states), an E-Way Bill must be generated before movement. This applies to supply, job work, or any other reason for movement.',
    'b2b_sales_pct', '>', '0', 'numeric',
    'annual_turnover_cr', '>=', '0.20', 'numeric',
    'MEDIUM', 'Continuous', 0, 10000,
    '₹10,000 or tax evaded — whichever is higher. Goods can be seized.',
    '["Register on E-Way Bill portal at ewaybillgst.gov.in", "Generate EWB before goods leave your premises", "EWB valid for 1 day per 200km distance", "Train warehouse/logistics staff to generate EWB", "EWB not required for goods below ₹50,000 or exempted categories"]',
    'CGST Rules 138 to 138D; Notification No. 15/2018-Central Tax', 'https://ewaybillgst.gov.in',
    '2018-04-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'GST-008-v1', 'GST-008', 1,
    'GST', 'TDS',
    'GST TDS Applicable (Government Contracts)',
    'If you supply goods or services to government entities (Central/State Government, PSUs), they are required to deduct 2% GST TDS from payments above ₹2.5 Lakh. You must reconcile TDS credits in GSTR-7A and claim in your returns.',
    'annual_turnover_cr', '>=', '0.20', 'numeric',
    'b2b_sales_pct', '>', '0', 'numeric',
    'LOW', 'Continuous', 0, 0,
    'No penalty on supplier — deduction is made by government entity. But failure to reconcile means lost credits.',
    '["Check GSTR-7A monthly for TDS deducted by government buyers", "Reconcile TDS credits with your GSTR-3B", "Contact government entity if TDS not reflected — they must file GSTR-7", "Claim TDS credit while filing GSTR-3B monthly"]',
    'CGST Act 2017, Section 51; CBIC Circular No. 76/50/2018', 'https://gst.gov.in',
    '2018-10-01', NULL, 1, 0, 0,
    datetime('now')
);

-- ============================================================
-- RBI RULES
-- NOTE: All RBI Digital Lending rules below are updated to reflect
-- RBI (Digital Lending) Directions, 2025 (dated May 8, 2025),
-- which repealed and replaced the Guidelines on Digital Lending
-- dated September 2, 2022.
-- Official notification: RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26
-- ============================================================

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-001-v1', 'RBI-001', 1,
    'RBI', 'Digital Lending',
    'Key Fact Statement (KFS) Mandatory Before Loan Sanction',
    'As a digital lender, you must provide every borrower a standardised Key Fact Statement (KFS) before executing the loan contract. KFS must show Annual Percentage Rate (APR) — including ALL costs, not just interest — EMI schedule, all fees, penal charges, and grievance contact. Borrower must acknowledge receipt.',
    'has_digital_lending_app', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Continuous', 0, 500000,
    'Up to ₹5 Lakh per incident for violating KFS requirements. RBI can also restrict lending operations.',
    '["Design KFS template per RBI standardised format (Annex I of DL Directions 2025)", "Ensure APR calculation includes: interest + processing fee + insurance + all other charges", "Build KFS generation into loan origination system — auto-populate before sanction", "Obtain digital acknowledgement from borrower (timestamp it)", "KFS must be available in regional language on request", "Archive KFS for each loan for 5 years minimum"]',
    'RBI (Digital Lending) Directions, 2025, dated May 8, 2025; RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26',
    'https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12848',
    '2025-05-08', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-002-v1', 'RBI-002', 1,
    'RBI', 'Digital Lending',
    'Direct Fund Flow — No LSP Pass-Through Accounts',
    'All loan disbursals must flow DIRECTLY from the Regulated Entity (RE) bank account to the borrower bank account. All repayments must flow DIRECTLY from borrower to RE. LSPs and DLAs cannot hold borrower funds in any pool, escrow, or transit account. This is a fundamental operational requirement — not a suggestion.',
    'has_digital_lending_app', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Continuous', 0, 2000000,
    'Up to ₹2 Crore penalty. RBI can cancel NBFC license for systematic violations.',
    '["Audit all current payment flows — map every account funds pass through", "Identify and eliminate any LSP pool/escrow accounts in the flow", "Restructure payment architecture: RE bank → Borrower bank (direct)", "Update all LSP agreements to remove fund-holding arrangements", "Conduct end-to-end test with compliance team sign-off", "Document the new flow and get board approval", "Submit architecture to RBI if required"]',
    'RBI (Digital Lending) Directions, 2025, dated May 8, 2025; RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26',
    'https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12848',
    '2025-05-08', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-003-v1', 'RBI-003', 1,
    'RBI', 'Digital Lending',
    'Cooling-Off Period — Borrower Exit Rights',
    'Every borrower must be given a mandatory cooling-off period to exit the loan without penalty (except a nominal one-time processing fee if charged). The duration of the cooling-off period is determined by the RE''s board of directors and must be disclosed in the KFS — the minimum is 1 day, irrespective of loan tenure. During this period, if the borrower exits, only proportionate interest for days used is charged. The earlier fixed 3-day / 1-day tenure-based rule has been replaced by this board-determined minimum under the 2025 Directions.',
    'has_digital_lending_app', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Continuous', 0, 200000,
    '₹2 Lakh per violation. Class action risk from borrowers.',
    '["Board of Directors must formally determine and approve the cooling-off period (minimum 1 day)", "Document the board-approved cooling-off period in your lending policy", "Disclose the cooling-off period prominently in the KFS before loan sanction", "Build opt-out mechanism in DLA (easy-to-find exit button)", "Configure system to accept prepayment within cooling-off period — only proportionate interest charged", "A nominal one-time processing fee may be charged if exiting during cooling-off, but no prepayment penalties", "Log all cooling-off exits in audit trail", "Train customer service team on this right"]',
    'RBI (Digital Lending) Directions, 2025, dated May 8, 2025; RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26',
    'https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12848',
    '2025-05-08', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-004-v1', 'RBI-004', 1,
    'RBI', 'Digital Lending',
    'Data Privacy — Prohibited DLA Data Access',
    'Your Digital Lending App is prohibited from accessing contact list, call logs, or phone gallery/storage on a continuous basis. Data collection must be purpose-specific, consent-based, and minimal. One-time access to camera, microphone, and location is permitted with explicit consent for KYC needs. All borrower data must be stored within India; if processed overseas, it must be repatriated and deleted from foreign servers within 24 hours. Biometric data cannot be stored unless specifically required by regulation.',
    'has_digital_lending_app', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Continuous', 0, 1000000,
    '₹1 Crore per DLA for data privacy violations. Play Store/App Store removal risk.',
    '["Audit current app permissions — list every permission requested", "Remove any permissions for: READ_CONTACTS, READ_CALL_LOG, READ_EXTERNAL_STORAGE, CAMERA (continuous)", "Implement one-time permission requests with clear use-case explanation to user (e.g. one-time KYC)", "Ensure all borrower data is stored on servers within India", "If any overseas processing occurs, implement 24-hour data repatriation and deletion from foreign servers", "Remove any feature that contacts borrower friends/family for recovery", "Add privacy policy disclosure on app store listing and RE website", "Conduct app privacy audit quarterly"]',
    'RBI (Digital Lending) Directions, 2025, dated May 8, 2025; RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26',
    'https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12848',
    '2025-05-08', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-005-v1', 'RBI-005', 1,
    'RBI', 'Digital Lending',
    'DLG Cap — 5% Maximum Default Loss Guarantee from LSP',
    'If your LSP provides a Default Loss Guarantee (DLG) — formerly known as First Loss Default Guarantee (FLDG) — the guarantee cannot exceed 5% of the loan portfolio outstanding at the beginning of each quarter. DLG arrangements are prohibited for: revolving credit facilities, loans covered under credit guarantee scheme trust funds, and loans facilitated by NBFC-P2P platforms. Implicit guarantees of any kind are prohibited. All DLG arrangements must be documented in a formal contractual agreement and must be explicit. Only LSPs incorporated under the Companies Act, 2013 are eligible DLG providers.',
    'uses_lsp', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Quarterly', 90, 500000,
    '₹5 Lakh penalty + mandatory unwinding of excess DLG. Can trigger license review.',
    '["Calculate current DLG exposure as % of loan portfolio at quarter start", "Review all LSP agreements for DLG/FLDG clauses — update terminology to DLG", "Verify LSP is incorporated under Companies Act, 2013 — ineligible providers must unwind arrangements", "Check DLG is not applied to: revolving credit, CGTS-covered loans, or NBFC-P2P facilitated loans", "If DLG > 5%: renegotiate cap with LSP before quarter end", "Remove any implicit guarantee language from LSP contracts", "Ensure DLG arrangement is backed by a formal contractual agreement", "Set up quarterly DLG monitoring report", "Board must approve all DLG arrangements"]',
    'RBI (Digital Lending) Directions, 2025, dated May 8, 2025; RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26',
    'https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12848',
    '2025-05-08', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-006-v1', 'RBI-006', 1,
    'RBI', 'NBFC Compliance',
    'NBFC Net Owned Fund (NOF) Minimum ₹2 Crore',
    'All NBFCs must maintain a minimum Net Owned Fund (NOF) of ₹2 Crore at all times. NOF = Paid-up equity capital + Preference shares + Free reserves - Accumulated losses - Intangible assets - Deferred revenue expenditure. Falling below triggers license cancellation process.',
    'has_nbfc_license', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Continuous', 0, 5000000,
    'License cancellation if NOF falls below ₹2 Crore. Criminal liability for directors.',
    '["Calculate NOF monthly: Paid-up capital + Reserves - Losses - Intangibles", "Set alert at ₹2.5 Cr (buffer before breach)", "If approaching breach: plan rights issue, promoter infusion, or merger", "Report NOF to RBI in monthly returns (Form NBS-7)", "Board must review NOF quarterly"]',
    'RBI Master Direction - Non-Banking Financial Company — Scale Based Regulation, 2023, Para 4',
    'https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12550',
    '2022-10-01', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-007-v1', 'RBI-007', 1,
    'RBI', 'NBFC Compliance',
    'Grievance Redressal — Nodal Officer and 30-Day Resolution',
    'Digital lenders must appoint a Nodal Grievance Redressal Officer. All customer complaints must be resolved within 30 days. If unresolved, borrower can escalate to RBI Ombudsman at no cost. Contact details of Nodal Officer must be prominently displayed in DLA and on website.',
    'has_digital_lending_app', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'MEDIUM', 'Continuous', 0, 100000,
    '₹1 Lakh per complaint not resolved within 30 days. Ombudsman can issue ex-parte orders.',
    '["Appoint a named Nodal Grievance Redressal Officer (must be senior executive)", "Create dedicated grievance email ID and phone number", "Display officer contact on DLA home screen and website footer", "Set up complaint tracking system with 30-day SLA alerts", "Train customer service team on complaint escalation process", "Submit quarterly grievance report to board"]',
    'RBI Digital Lending Guidelines 2022, Para 6; RBI Integrated Ombudsman Scheme 2021',
    'https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12382',
    '2022-09-02', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'RBI-008-v1', 'RBI-008', 1,
    'RBI', 'NBFC Compliance',
    'Monthly Regulatory Returns — NBFC NBS Filing',
    'NBFCs must file monthly regulatory returns to RBI. Key forms: NBS-1 (income/expenditure), NBS-7 (capital funds and risk assets ratio). Quarterly: NBS-2 (assets and liabilities). Annual: NBS-4 (profits/losses). Late filing attracts ₹100 per day for Base Layer NBFCs.',
    'has_nbfc_license', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Monthly', 15, 10000,
    '₹100 per day for NBFC-BL. Higher for upper layers. Repeat violations trigger license review.',
    '["Set up COSMOS portal access (RBI reporting portal)", "Calendar all NBS filing deadlines: NBS-1 by 7th, NBS-7 by 15th", "Designate responsible officer for each return", "Automate data extraction from your core banking/lending system", "Build internal review before submission (at least 2 approvers)", "Archive all submitted returns for 8 years"]',
    'RBI Master Direction NBFC SBR 2023, Annex XVI; COSMOS Portal',
    'https://rbi.org.in',
    '2022-10-01', NULL, 1, 0, 0,
    datetime('now')
);

-- ============================================================
-- MSME RULES
-- ============================================================

INSERT OR IGNORE INTO thresholds VALUES (
    'MSME-001-v1', 'MSME-001', 1,
    'MSME', 'Registration',
    'Udyam Registration — Unlock MSME Benefits',
    'Your business qualifies as an MSME based on turnover (≤₹250 Crore) and investment criteria. Udyam Registration is free, online, and mandatory to access: CGTMSE guarantee, priority sector lending, government procurement preference (25% reserved), delayed payment protection, and subsidies.',
    'annual_turnover_cr', '<=', '250.0', 'numeric',
    'has_udyam_registration', '==', '0', 'boolean',
    'MEDIUM', 'One-time', 30, 0,
    'No direct penalty. But without Udyam, you cannot access CGTMSE, priority sector loans, or enforce MSMED Act delayed payment rights.',
    '["Visit udyamregistration.gov.in", "Keep Aadhaar of proprietor/director/partner ready", "Keep PAN of business entity ready", "Self-declare investment and turnover figures", "Submit — certificate generated instantly", "Update bank records, loan applications with Udyam number", "File annual self-declaration to maintain classification"]',
    'MSMED Act 2006 as amended by Finance Act 2020; DPIIT Notification S.O. 2119(E)',
    'https://udyamregistration.gov.in',
    '2020-07-01', NULL, 1, 0, 1,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'MSME-002-v1', 'MSME-002', 1,
    'MSME', 'Benefits',
    'CGTMSE Collateral-Free Loan — Up to ₹2 Crore',
    'As a Micro or Small Enterprise, you are eligible for collateral-free loans up to ₹2 Crore under the Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE). The government guarantees 75-85% of the loan to the bank — you do not need to pledge property.',
    'annual_turnover_cr', '<=', '50.0', 'numeric',
    'has_udyam_registration', '==', '1', 'boolean',
    'LOW', 'One-time', 0, 0,
    'No penalty. This is a benefit — failure to use it means paying higher interest or providing collateral unnecessarily.',
    '["Ensure Udyam Registration is active and updated", "Approach any scheduled commercial bank or NBFC", "Request CGTMSE-covered loan — bank applies for guarantee cover", "Loan amount up to ₹2 Crore without any collateral", "Guarantee fee: 0.37%-1.35% of loan amount per year (paid by bank)"]',
    'CGTMSE Scheme Guidelines; MSMED Act 2006 Section 9', 'https://cgtmse.in',
    '2000-08-01', NULL, 1, 0, 1,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'MSME-003-v1', 'MSME-003', 1,
    'MSME', 'Payment Protection',
    'MSMED Act Delayed Payment Protection — 45-Day Rule',
    'Under the MSMED Act, buyers must pay your invoices within 45 days of acceptance (15 days if no written agreement). If payment is delayed, you are entitled to compound interest at 3x the RBI Bank Rate (currently ~31.5% p.a. compound) from the day after the due date. You can file a case at the MSME Facilitation Council.',
    'annual_turnover_cr', '<=', '250.0', 'numeric',
    'has_udyam_registration', '==', '1', 'boolean',
    'MEDIUM', 'Continuous', 0, 0,
    'No penalty on you — this is your right to recover from late-paying buyers.',
    '["Track all outstanding invoices with acceptance dates", "Calculate 45-day deadline for each invoice", "Send reminder on day 30, formal notice on day 45", "Calculate interest at 3x RBI Bank Rate (compounded monthly)", "File complaint at MSME Facilitation Council if no response within 15 days", "Large listed buyers must disclose MSME dues in annual reports — use as leverage"]',
    'MSMED Act 2006, Sections 15-23; DPIIT Notifications',
    'https://samadhaan.msme.gov.in',
    '2006-10-02', NULL, 1, 0, 1,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'MSME-004-v1', 'MSME-004', 1,
    'MSME', 'Classification Alert',
    'MSME Classification at Risk — Approaching Medium Enterprise Limit',
    'Your turnover is approaching ₹250 Crore — the upper limit for Medium Enterprise classification. Crossing this threshold means losing ALL MSME benefits: CGTMSE, priority sector lending, procurement preference, delayed payment protection. Plan 12 months in advance.',
    'annual_turnover_cr', '>=', '200.0', 'numeric',
    'annual_turnover_cr', '<=', '250.0', 'numeric',
    'HIGH', 'One-time', 365, 0,
    'No direct penalty but loss of MSME benefits can be worth ₹1-50 Crore depending on loans and contracts.',
    '["Project turnover for next 3 years with your finance team", "Consult a CA on structuring options (subsidiary, LLP split)", "Review all CGTMSE-backed loans — plan refinancing", "Review government contracts — will procurement preference be lost?", "Consider Udyam re-registration strategy", "Board must make structural decision 12 months before crossing"]',
    'MSMED Act 2006 as amended 2020; Investment and turnover criteria notification',
    'https://udyamregistration.gov.in',
    '2020-07-01', NULL, 1, 1, 0,
    datetime('now')
);

-- ============================================================
-- LABOUR / PF / ESI RULES
-- ============================================================

INSERT OR IGNORE INTO thresholds VALUES (
    'PF-001-v1', 'PF-001', 1,
    'PF_ESI', 'Labour Compliance',
    'Provident Fund (PF) Registration Mandatory',
    'Your business has 20 or more employees. Registration with the Employees Provident Fund Organisation (EPFO) is mandatory. Both employer and employee contribute 12% of basic salary to PF. Employer also contributes to EPS (Employee Pension Scheme) and EDLI (Insurance).',
    'employee_count', '>=', '20', 'numeric',
    NULL, NULL, NULL, NULL,
    'HIGH', 'One-time', 30, 50000,
    'Penalty of ₹5,000 + damages at 5-25% of arrears. Criminal prosecution for willful default.',
    '["Register on EPFO Unified Portal at unifiedportal-emp.epfindia.gov.in", "Obtain Employer PF Registration Number", "Deduct 12% of basic salary from employee salary", "Contribute employer share: 12% of basic (3.67% PF + 8.33% EPS + 0.5% EDLI + 0.5% admin)", "File ECR (Electronic Challan cum Return) monthly by 15th", "Issue PF slips to employees annually"]',
    'Employees Provident Funds and Miscellaneous Provisions Act 1952, Section 1(3)',
    'https://unifiedportal-emp.epfindia.gov.in',
    '1952-03-04', NULL, 1, 0, 0,
    datetime('now')
);

INSERT OR IGNORE INTO thresholds VALUES (
    'ESI-001-v1', 'ESI-001', 1,
    'PF_ESI', 'Labour Compliance',
    'ESI (Employee State Insurance) Registration Mandatory',
    'Your business has 10 or more employees (in some states 20+) earning up to ₹21,000/month. Registration with ESIC is mandatory. Employer contributes 3.25% of wages, employee contributes 0.75%. Provides health insurance and disability benefits to covered employees.',
    'employee_count', '>=', '10', 'numeric',
    NULL, NULL, NULL, NULL,
    'HIGH', 'One-time', 15, 25000,
    'Penalty: 12% p.a. interest on delayed contributions. Double contribution as damages for willful default.',
    '["Register on ESIC portal at esic.in", "Obtain Employer Code Number", "Identify employees with salary ≤ ₹21,000/month — they are covered", "Deduct 0.75% from employee salary", "Pay 3.25% employer contribution", "File ESI returns half-yearly", "Display ESI registration certificate at workplace"]',
    'Employees State Insurance Act 1948, Section 1(5)',
    'https://esic.in',
    '1948-04-19', NULL, 1, 0, 0,
    datetime('now')
);

-- ============================================================
-- MCA / COMPANIES ACT RULES
-- ============================================================

INSERT OR IGNORE INTO thresholds VALUES (
    'MCA-001-v1', 'MCA-001', 1,
    'MCA', 'Annual Compliance',
    'Annual ROC Filings Mandatory (Private Limited Companies)',
    'As a Private Limited Company, you must file annual returns and financial statements with the Registrar of Companies (ROC) every year. Key forms: MGT-7 (Annual Return by 60 days from AGM), AOC-4 (Financial Statements by 30 days from AGM). AGM must be held within 6 months of financial year end.',
    'entity_type', '==', 'Private Limited', 'string',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Annual', 273, 50000,
    'Additional fee: ₹100 per day after due date. Serious default leads to company strike-off.',
    '["Hold Annual General Meeting (AGM) before 30th September", "Prepare audited financial statements", "File AOC-4 within 30 days of AGM (financial statements)", "File MGT-7/7A within 60 days of AGM (annual return)", "Ensure DIN of all directors is active and KYC done (DIR-3 KYC annually)", "File ADT-1 for auditor appointment (new auditor)"]',
    'Companies Act 2013, Sections 92, 96, 137; Companies (Management and Administration) Rules 2014',
    'https://mca.gov.in',
    '2014-04-01', NULL, 1, 0, 0,
    datetime('now')
);

-- ============================================================
-- SEBI RULES
-- ============================================================

INSERT OR IGNORE INTO thresholds VALUES (
    'SEBI-001-v1', 'SEBI-001', 1,
    'SEBI', 'Listing Obligations',
    'SEBI LODR — Quarterly Results and Disclosures',
    'As a listed company, you must comply with SEBI (Listing Obligations and Disclosure Requirements) Regulations 2015. Key obligations: quarterly financial results within 45 days of quarter end, annual results within 60 days of FY end, material event disclosures within 24 hours, board meeting intimation 2 days in advance.',
    'is_listed', '==', '1', 'boolean',
    NULL, NULL, NULL, NULL,
    'HIGH', 'Quarterly', 45, 1000000,
    '₹1-5 Lakh per non-compliance instance. Trading halt on the stock. Reputational damage.',
    '["Set quarterly calendar: results within 45 days of each quarter end", "Appoint Company Secretary — mandatory for listed companies", "Establish board committee structure (Audit, Nomination, Stakeholder)", "Set up insider trading policy and trading window calendar", "File all disclosures on stock exchange portal within 24 hours of board decision", "Ensure website has investor relations section with all disclosures"]',
    'SEBI (LODR) Regulations 2015, Regulation 33 and 47',
    'https://sebi.gov.in/legal/regulations/mar-2015/sebi-listing-obligations-and-disclosure-requirements-regulations-2015_30575.html',
    '2015-12-01', NULL, 1, 0, 0,
    datetime('now')
);