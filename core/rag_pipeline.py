"""
core/rag_pipeline.py
ChromaDB vector store — ingests regulatory docs, enables semantic search.
"""
import os
import json
from pathlib import Path
from typing import List
from datetime import datetime

CHROMA_DIR = str(Path(__file__).parent.parent / "data" / "chroma_db")
COLLECTION  = "regulatory_clauses"

# ── Regulatory text corpus (embedded at startup — no PDF needed for demo) ────
REGULATORY_CORPUS = [
    # ------------------------------------------------------------------
    # RBI entries updated to RBI (Digital Lending) Directions, 2025
    # (dated May 8, 2025) which repealed the 2022 Guidelines.
    # Notification: RBI/2025-26/36 DOR.STR.REC.19/21.07.001/2025-26
    # ------------------------------------------------------------------
    {
        "doc_id": "rbi_dl_2025_fund_flow",
        "regulator": "RBI",
        "doc_title": "RBI (Digital Lending) Directions, 2025 — Fund Flow",
        "effective_date": "2025-05-08",
        "text": """
RBI (Digital Lending) Directions, 2025 — Direct Fund Flow Requirements
All loan disbursals by Regulated Entities (REs) must be executed directly into
the bank account of the borrower without routing through any intermediary account.
Disbursals to third-party accounts, including those of LSPs, are not permitted
unless explicitly allowed by regulation (e.g. co-lending between REs, or
disbursals for specific end-use such as gold loans, education, real estate).
All loan repayments must be made directly from the borrower's bank account to
the RE's bank account. No pass-through or pool accounts of the LSP, the DLA,
or any other third party shall be used for loan servicing.
The movement of funds between the borrower and the RE must not be controlled
by any third party — this is a new explicit prohibition added in the 2025 Directions.
Any fees payable to LSPs shall be paid directly by the RE and shall not be
charged to the borrower by the LSP.
Nodal grievance redressal officer must be appointed by RE. Contact details of
the nodal officer and LSP grievance officer must be displayed on the DLA.
Borrower complaints must be resolved within 30 days before escalation to
RBI Ombudsman is permitted. RE must also publish a link to RBI's Complaint
Management System (CMS) and the Sachet Portal on its website and DLA.
""",
    },
    {
        "doc_id": "rbi_dl_2025_kfs",
        "regulator": "RBI",
        "doc_title": "RBI (Digital Lending) Directions, 2025 — KFS and Disclosure",
        "effective_date": "2025-05-08",
        "text": """
Key Fact Statement (KFS) — Mandatory Pre-Loan Disclosure
Before execution of the loan contract, the RE must provide the borrower with
a Key Fact Statement (KFS) in standardised format.
KFS must contain: Annual Percentage Rate (APR) inclusive of all charges,
loan amount, EMI amount, tenure, processing fees, prepayment charges,
penal charges (shown event-wise, not annualised), and contact details of
grievance officer.
APR is the annualised interest rate inclusive of all other costs associated
with the credit — not just the nominal interest rate.
Borrower must digitally acknowledge receipt of KFS before loan disbursal.
KFS must be available in English and the local language on request.
Digitally signed documents including the sanction letter and terms and
conditions must be sent to the borrower via email or SMS.
Cooling-off period (updated under 2025 Directions): The RE's board of directors
must determine the cooling-off period — the minimum is 1 day regardless of
loan tenure. During this period the borrower may exit the loan by paying only
proportionate APR-based interest. A disclosed one-time processing fee may also
be charged — but no other prepayment penalties apply during the cooling-off period.
NOTE: The earlier fixed rule of 3 days for loans ≥ 7 days and 1 day for loans
< 7 days has been replaced. The board-determined minimum of 1 day now applies
irrespective of loan tenure.
Credit limit increases on revolving credit products require explicit borrower
request and consent — automatic limit hikes without consent are prohibited.
""",
    },
    {
        "doc_id": "rbi_dl_2025_data",
        "regulator": "RBI",
        "doc_title": "RBI (Digital Lending) Directions, 2025 — Data Privacy",
        "effective_date": "2025-05-08",
        "text": """
Data Privacy and Security Requirements for Digital Lending Apps
Digital Lending Apps (DLAs) must not access mobile phone resources like
contact lists, call logs, phone galleries, or phone storage on a continuous basis.
One-time access to camera, microphone, and location is permitted only with
explicit borrower consent and only when required for specific functionality (e.g. KYC).
Collection of data must be need-based, purpose-specific, and with explicit consent.
Borrowers must be able to revoke permissions and request data deletion.
Data obtained by DLAs must be used only for the purpose for which it was collected.
Biometric data cannot be stored by DLAs or LSPs unless specifically required by law.
DLAs must have a comprehensive privacy policy available on app stores and the RE website.
Borrowers must not be contacted by accessing their phone contacts for recovery purposes.
Data localisation (updated under 2025 Directions): All borrower data must be
stored on servers within India. Offshore processing is now explicitly permitted,
but data processed outside India must be deleted from foreign servers and
transferred back to India within 24 hours of processing.
This 24-hour repatriation rule is a new addition in the 2025 Directions — the
2022 Guidelines required only local storage and were silent on offshore processing.
Data obligations are now aligned with the Digital Personal Data Protection
(DPDP) Act, 2023 requirements.
Borrowers must not be contacted by DLA or LSP recovery agents without prior
communication via email or SMS disclosing the identity of the recovery agent.
""",
    },
    {
        "doc_id": "rbi_dl_2025_dlg",
        "regulator": "RBI",
        "doc_title": "RBI (Digital Lending) Directions, 2025 — Default Loss Guarantee (DLG)",
        "effective_date": "2025-05-08",
        "text": """
Default Loss Guarantee (DLG) Provisions — formerly called FLDG
The instrument is now formally called Default Loss Guarantee (DLG).
First Loss Default Guarantee (FLDG) is the legacy term used prior to 2023.
Regulated Entities may accept DLG from LSPs subject to strict conditions.
DLG from an LSP is capped at 5% of the loan portfolio outstanding at the
beginning of each quarter — this cap remains unchanged from prior guidelines.
Eligibility for DLG provider: RE can only enter DLG arrangements with an LSP
or another RE acting as an LSP. The LSP providing DLG must be incorporated
under the Companies Act, 2013 — unincorporated entities cannot be DLG providers.
Restrictions on DLG arrangements (new under 2025 Directions):
REs are prohibited from entering DLG arrangements for:
(i) revolving credit facilities offered through digital lending channels or credit cards;
(ii) loans already covered under credit guarantee schemes managed by trust funds
    (e.g. CGTMSE-backed loans);
(iii) loans facilitated by NBFC-P2P platforms.
Implicit guarantees of any kind are not permitted. All DLG arrangements must
be explicit, documented in a formal contract, and legally enforceable.
RE must conduct enhanced due diligence on DLG providers including review of
eligibility, nature and extent of DLG cover, and ongoing monitoring.
Details of DLG arrangements finalised in a month must be published on the
LSP's website within 7 working days of the following month.
Quarterly reporting of DLG exposure must be submitted to RBI.
Synthetic structures that create implicit guarantee without being labelled DLG
are prohibited.
""",
    },
    {
        "doc_id": "gst_einvoice_2023",
        "regulator": "GST",
        "doc_title": "CBIC E-Invoicing Notification — August 2023",
        "effective_date": "2023-08-01",
        "text": """
CBIC Notification No. 17/2022-Central Tax — E-Invoice Threshold Change
With effect from August 1, 2023, the threshold for mandatory e-invoicing
has been reduced from Rs. 10 crore to Rs. 5 crore of aggregate annual turnover.
All registered persons whose aggregate annual turnover in any preceding financial
year exceeds Rs. 5 crore must generate e-invoices for all B2B transactions.
E-invoice is generated by registering the invoice on the Invoice Registration
Portal (IRP) which assigns a unique Invoice Reference Number (IRN).
The IRN along with a QR code must be present on the invoice shared with the buyer.
Failure to generate valid e-invoice means the invoice is not a valid tax document
and the buyer cannot claim Input Tax Credit (ITC) on such purchases.
Penalty: Rs. 10,000 per invoice or tax amount evaded — whichever is higher.
E-invoice is not required for B2C transactions, exports, and certain exempted categories.
""",
    },
    {
        "doc_id": "gst_qrmp_2021",
        "regulator": "GST",
        "doc_title": "GST QRMP Scheme — Quarterly Return Monthly Payment",
        "effective_date": "2021-01-01",
        "text": """
QRMP Scheme — Quarterly Return Monthly Payment for Small Taxpayers
Taxpayers with aggregate annual turnover up to Rs. 5 crore in the preceding
financial year are eligible to opt for QRMP scheme.
Under QRMP, taxpayers file GSTR-1 and GSTR-3B on quarterly basis.
Tax payments must be made monthly using PMT-06 challan.
Monthly tax payment: 35% of net cash tax liability of last quarter or
actual liability based on self-assessment — whichever is chosen.
Quarterly GSTR-1 due by 13th of month following the quarter.
Quarterly GSTR-3B due by 22nd or 24th of month following the quarter
depending on state of principal place of business.
Taxpayers with turnover exceeding Rs. 5 crore must mandatorily file monthly returns.
""",
    },
    {
        "doc_id": "gst_itc_rules",
        "regulator": "GST",
        "doc_title": "GST Input Tax Credit Rules and Restrictions",
        "effective_date": "2017-07-01",
        "text": """
Input Tax Credit (ITC) — Eligibility and Restrictions
ITC is available on goods and services used or intended to be used in the
course or furtherance of business.
ITC is NOT available on: food and beverages, outdoor catering, beauty treatment,
health services, cosmetic surgery, membership of clubs, rent-a-cab,
life insurance, health insurance (except mandatory), motor vehicles for personal use.
Conditions for ITC claim: (1) Tax invoice received and goods/services received.
(2) Tax charged has been paid to government by supplier. (3) Supplier has filed
return and supply reflects in GSTR-2B. (4) Payment made to supplier within 180 days.
ITC must be availed within the due date of September return of following FY or
annual return — whichever is earlier.
Reversal required for: exempt supplies, non-business use, non-payment to supplier
within 180 days, and where goods are used partly for taxable and partly exempt supply.
""",
    },
    {
        "doc_id": "msmed_act_2020",
        "regulator": "MSME",
        "doc_title": "MSMED Act 2020 Amendment — Classification and Payment",
        "effective_date": "2020-07-01",
        "text": """
MSME Classification — Revised Criteria 2020
Micro Enterprise: Investment in plant and machinery up to Rs. 1 crore
AND annual turnover up to Rs. 5 crore.
Small Enterprise: Investment up to Rs. 10 crore AND turnover up to Rs. 50 crore.
Medium Enterprise: Investment up to Rs. 50 crore AND turnover up to Rs. 250 crore.
Investment means investment in plant and machinery or equipment — excludes land and building.
Classification is based on aggregate of all units under same PAN.
Udyam Registration is the official registration — mandatory to avail MSME benefits.
Delayed Payment Provisions (Section 15-23):
Buyer must make payment to MSME supplier within 45 days of acceptance.
If no written agreement: payment within 15 days.
In case of delay: compound interest at 3 times RBI Bank Rate — compounded monthly.
Disputes to be referred to MSME Facilitation Council for conciliation and arbitration.
Buyers listed on stock exchange must disclose MSME outstanding dues in annual reports.
CGTMSE provides credit guarantee for collateral-free loans up to Rs. 2 crore to MSMEs.
Priority sector lending: banks must allocate 7.5% of ANBC to micro enterprises.
""",
    },
    {
        "doc_id": "rbi_nbfc_sbr_2022",
        "regulator": "RBI",
        "doc_title": "RBI NBFC Scale Based Regulation Framework 2022",
        "effective_date": "2022-10-01",
        "text": """
NBFC Scale Based Regulation — Four Layer Framework
Base Layer (NBFC-BL): NBFCs below Rs. 1000 crore asset size, not accepting deposits,
not in upper layers. Minimum NOF Rs. 2 crore. Basic compliance requirements.
Middle Layer (NBFC-ML): NBFCs with asset size above Rs. 1000 crore or deposit-taking
or holding HFC licenses or listed. Enhanced governance required.
Upper Layer (NBFC-UL): Top 10 NBFCs by asset size as identified by RBI. Near-bank compliance.
Net Owned Fund (NOF) = paid-up equity capital + preference shares + free reserves
minus accumulated losses minus intangible assets minus deferred revenue expenditure.
Minimum NOF: Rs. 2 crore for all NBFCs — mandatory at all times.
Monthly regulatory returns: NBS-1 income/expenditure, NBS-7 capital and risk assets.
Quarterly: NBS-2 assets and liabilities statement.
Credit information submission to all four CICs mandatory.
RBI inspection can be triggered for any NBFC at any time.
""",
    },
]


def get_vectorstore():
    """Get or create ChromaDB vectorstore."""
    try:
        import chromadb
        from langchain_community.vectorstores import Chroma
        from core.llm_provider import get_embeddings

        client = chromadb.PersistentClient(path=CHROMA_DIR)
        embeddings = get_embeddings()
        return Chroma(
            client=client,
            collection_name=COLLECTION,
            embedding_function=embeddings,
        )
    except Exception as e:
        print(f"⚠️  ChromaDB unavailable: {e}")
        return None


def load_corpus() -> int:
    """Load all regulatory text into ChromaDB. Safe to call multiple times."""
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.schema import Document

        vs = get_vectorstore()
        if not vs:
            return 0

        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
        all_docs = []

        for item in REGULATORY_CORPUS:
            doc = Document(
                page_content=item["text"].strip(),
                metadata={
                    "doc_id": item["doc_id"],
                    "regulator": item["regulator"],
                    "doc_title": item["doc_title"],
                    "effective_date": item["effective_date"],
                }
            )
            chunks = splitter.split_documents([doc])
            all_docs.extend(chunks)

        vs.add_documents(all_docs)
        return len(all_docs)
    except Exception as e:
        print(f"⚠️  Corpus load failed: {e}")
        return 0


def retrieve(query: str, k: int = 5) -> List[dict]:
    """Semantic search over regulatory corpus."""
    try:
        vs = get_vectorstore()
        if not vs:
            return []
        results = vs.similarity_search_with_score(query, k=k)
        return [
            {
                "content": doc.page_content,
                "regulator": doc.metadata.get("regulator", ""),
                "doc_title": doc.metadata.get("doc_title", ""),
                "effective_date": doc.metadata.get("effective_date", ""),
                "relevance": round(1 - score, 3),
            }
            for doc, score in results
        ]
    except Exception as e:
        print(f"⚠️  RAG retrieval failed: {e}")
        return []


def get_chroma_stats() -> dict:
    """Return basic stats."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        col = client.get_collection(COLLECTION)
        return {"chunks": col.count(), "status": "ready"}
    except Exception:
        return {"chunks": 0, "status": "not_loaded"}