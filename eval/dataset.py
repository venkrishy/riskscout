"""
Synthetic evaluation dataset — 20 financial documents with known expected decisions.
Each document is a realistic text representation of a loan application or financial statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalDocument:
    doc_id: str
    category: str
    expected_decision: str  # "approve" | "review" | "reject"
    document_text: str
    description: str
    expected_score_range: tuple[int, int] = field(default=(0, 100))


EVAL_DATASET: list[EvalDocument] = [
    # -----------------------------------------------------------------------
    # APPROVE cases (expected score < 40 — low risk)
    # -----------------------------------------------------------------------
    EvalDocument(
        doc_id="EVAL-001",
        category="loan_application",
        expected_decision="approve",
        expected_score_range=(0, 39),
        description="Strong SME with excellent financials",
        document_text="""
COMMERCIAL LOAN APPLICATION
Date: 2024-03-15
Borrower: Pinnacle Manufacturing LLC
Entity Type: LLC
Loan Amount: $2,500,000 USD
Loan Purpose: Equipment purchase and facility expansion
Collateral: Industrial machinery appraised at $3,800,000

FINANCIAL SUMMARY (FY2023):
Annual Revenue: $18,400,000
Net Income: $2,100,000
Debt-to-Income Ratio: 0.28
Credit Score: 780
Years in Business: 14

Key terms: fixed rate 6.5% APR, 84-month term, monthly payments of $37,200
No outstanding judgments, liens, or defaults on record.
Strong payment history across all existing credit facilities.
""",
    ),
    EvalDocument(
        doc_id="EVAL-002",
        category="loan_application",
        expected_decision="approve",
        expected_score_range=(0, 39),
        description="Established corporation, low leverage",
        document_text="""
TERM LOAN APPLICATION
Date: 2024-01-22
Borrower: Brightfield Technology Corp
Entity Type: Corporation
Loan Amount: $750,000 USD
Loan Purpose: Working capital and software development
Collateral: Accounts receivable $1,200,000

FINANCIAL SUMMARY (FY2023):
Annual Revenue: $9,200,000
Net Income: $980,000
Debt-to-Income Ratio: 0.22
Credit Score: 765
Years in Business: 9

No defaults, no pending litigation.
Borrower has existing relationship with institution since 2017.
""",
    ),
    EvalDocument(
        doc_id="EVAL-003",
        category="financial_statement",
        expected_decision="approve",
        expected_score_range=(0, 39),
        description="Investment-grade corporation",
        document_text="""
ANNUAL FINANCIAL STATEMENT — REVIEW REQUEST
Borrower: Oakwood Retail Group Corporation
Date: 2024-02-10
Loan Amount: $5,000,000 USD
Loan Purpose: Retail expansion — 3 new locations

Revenue FY2023: $42,000,000
Net Income FY2023: $5,600,000
DTI: 0.19
Credit Score: 812
Years in Business: 22

Collateral: Real estate holdings appraised at $8,500,000
No risk indicators identified. Strong covenant compliance history.
""",
    ),
    EvalDocument(
        doc_id="EVAL-004",
        category="loan_application",
        expected_decision="approve",
        expected_score_range=(0, 39),
        description="Healthcare practice with stable revenue",
        document_text="""
PROFESSIONAL PRACTICE LOAN APPLICATION
Borrower: Sunrise Medical Associates LLC
Date: 2024-04-01
Loan Amount: $1,800,000
Loan Purpose: Medical equipment acquisition
Collateral: Equipment $2,400,000 + real estate $1,100,000

Annual Revenue: $6,800,000
Net Income: $1,200,000
DTI: 0.25
Credit Score: 755
Years in Business: 11

Borrower operates 3 outpatient clinics. Stable patient revenue.
No liens, judgments, or defaults. Insurance receivables strong.
""",
    ),
    EvalDocument(
        doc_id="EVAL-005",
        category="contract",
        expected_decision="approve",
        expected_score_range=(0, 39),
        description="Government contractor, low risk",
        document_text="""
CONTRACT FINANCING APPLICATION
Borrower: Federal Systems Group LLC
Date: 2024-03-28
Loan Amount: $3,200,000
Loan Purpose: Bridge financing for government contract fulfillment
Collateral: Government contract receivables $4,100,000

Annual Revenue: $22,000,000
Net Income: $2,800,000
DTI: 0.20
Credit Score: 790
Years in Business: 16

Primary revenue from Federal agencies (DoD, GSA). Low counterparty risk.
Contract backlog: $38M. No default history.
""",
    ),
    EvalDocument(
        doc_id="EVAL-006",
        category="loan_application",
        expected_decision="approve",
        expected_score_range=(0, 39),
        description="Real estate investor, conservative LTV",
        document_text="""
REAL ESTATE INVESTMENT LOAN APPLICATION
Borrower: Sterling Capital Partners LLC
Date: 2024-02-14
Loan Amount: $4,500,000
Loan Purpose: Acquisition of commercial office building
Collateral: Office building appraised at $7,200,000 (63% LTV)

Annual Revenue: $14,000,000
Net Income: $3,100,000
DTI: 0.30
Credit Score: 748
Years in Business: 13

Borrower portfolio: 8 commercial properties, 97% occupancy average.
No delinquencies. Existing debt service coverage ratio: 1.72x.
""",
    ),
    # -----------------------------------------------------------------------
    # REVIEW cases (expected score 40-79 — moderate risk)
    # -----------------------------------------------------------------------
    EvalDocument(
        doc_id="EVAL-007",
        category="loan_application",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Startup with limited operating history",
        document_text="""
SBA LOAN APPLICATION
Borrower: NexaVenture Technologies Inc
Date: 2024-01-15
Loan Amount: $1,200,000
Loan Purpose: Product launch and market expansion
Collateral: IP portfolio (estimated value $800,000)

Annual Revenue: $450,000 (partial year)
Net Income: -$220,000 (pre-revenue phase losses)
DTI: N/A
Credit Score: 680
Years in Business: 1.5

Founders have prior successful exits. Letters of intent from 3 enterprise clients.
No prior defaults. Some revenue concentration risk with top 2 clients at 85% of pipeline.
""",
    ),
    EvalDocument(
        doc_id="EVAL-008",
        category="financial_statement",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Mid-size retailer with margin pressure",
        document_text="""
REVOLVING CREDIT FACILITY — ANNUAL REVIEW
Borrower: Metro Retail Holdings Corporation
Date: 2024-03-10
Facility Amount: $8,000,000
Loan Purpose: Inventory and working capital

Annual Revenue: $31,000,000 (down 12% YoY)
Net Income: $620,000 (down 58% YoY)
DTI: 0.51
Credit Score: 695
Years in Business: 18

Risk indicators: Margin compression due to supply chain costs.
Two quarters of declining comparable store sales.
Covenant: Minimum EBITDA $2M — currently at $2.1M (near breach).
No defaults. One delinquent trade payable account identified.
""",
    ),
    EvalDocument(
        doc_id="EVAL-009",
        category="loan_application",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Restaurant group with pandemic recovery debt",
        document_text="""
COMMERCIAL LOAN APPLICATION
Borrower: Urban Hospitality Group LLC
Date: 2024-04-20
Loan Amount: $3,500,000
Loan Purpose: Refinancing + new location opening
Collateral: Restaurant equipment and lease assignments $2,100,000

Annual Revenue: $12,400,000
Net Income: $480,000
DTI: 0.62
Credit Score: 710
Years in Business: 8

Risk indicators: High leverage from 2021 pandemic-era EIDL loans still outstanding.
Revenue recovering — up 22% YoY. DSCR: 1.18x.
Related-party transaction: $200K loan from principal's family trust.
""",
    ),
    EvalDocument(
        doc_id="EVAL-010",
        category="contract",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Construction company, concentration risk",
        document_text="""
PROJECT FINANCING APPLICATION
Borrower: Summit Build & Development Corp
Date: 2024-02-28
Loan Amount: $6,200,000
Loan Purpose: Residential development project — 42 units
Collateral: Land and construction in progress $5,800,000

Annual Revenue: $19,000,000
Net Income: $1,400,000
DTI: 0.48
Credit Score: 724
Years in Business: 12

Risk indicators: Project concentration — this single project represents 71% of 2024 revenue.
Material costs 18% over budget. One prior mechanic's lien (resolved 2022).
Market: Moderate housing demand softening observed.
""",
    ),
    EvalDocument(
        doc_id="EVAL-011",
        category="loan_application",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Transportation company with regulatory issues",
        document_text="""
EQUIPMENT LOAN APPLICATION
Borrower: TransRoute Logistics LLC
Date: 2024-01-30
Loan Amount: $2,800,000
Loan Purpose: Fleet expansion — 18 commercial trucks
Collateral: Vehicle fleet appraised at $3,200,000

Annual Revenue: $16,800,000
Net Income: $890,000
DTI: 0.44
Credit Score: 715
Years in Business: 10

Risk indicators: FMCSA safety audit — 2 out-of-service violations in past 12 months.
Driver turnover at 38% (industry average 22%). Fuel hedging program expired.
No financial defaults. Operating authority in good standing.
""",
    ),
    EvalDocument(
        doc_id="EVAL-012",
        category="financial_statement",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Family business, succession planning uncertainty",
        document_text="""
TERM LOAN — FINANCIAL REVIEW
Borrower: Hartwell Family Enterprises LLC
Date: 2024-03-05
Loan Amount: $4,100,000
Loan Purpose: Owner buyout / succession financing
Collateral: Business assets $3,800,000

Annual Revenue: $14,500,000
Net Income: $1,600,000
DTI: 0.55
Credit Score: 735
Years in Business: 32

Risk indicators: Key-man risk — founder (age 71) transitioning to 3 family members.
No formal succession plan documented. Key customer (28% revenue) informal relationship
with founder personally. Life insurance policy on founder $2M.
""",
    ),
    EvalDocument(
        doc_id="EVAL-013",
        category="loan_application",
        expected_decision="review",
        expected_score_range=(40, 79),
        description="Cannabis business, regulatory complexity",
        document_text="""
COMMERCIAL REAL ESTATE LOAN
Borrower: Green Valley Dispensary Holdings LLC
Date: 2024-04-15
Loan Amount: $3,900,000
Loan Purpose: Dispensary property acquisition
Collateral: Commercial real estate $5,400,000

Annual Revenue: $8,700,000
Net Income: $1,100,000
DTI: 0.42
Credit Score: 690
Years in Business: 4

Risk indicators: Cannabis industry regulatory risk — state-licensed but federal scheduling uncertainty.
Limited banking relationships due to industry. Cash-heavy operations.
No prior defaults. License in good standing (Colorado MED).
""",
    ),
    # -----------------------------------------------------------------------
    # REJECT cases (expected score >= 80 — high risk)
    # -----------------------------------------------------------------------
    EvalDocument(
        doc_id="EVAL-014",
        category="loan_application",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Heavily indebted company with defaults",
        document_text="""
EMERGENCY CREDIT FACILITY APPLICATION
Borrower: Cascade Retail Corp
Date: 2024-02-01
Loan Amount: $12,000,000
Loan Purpose: Debt restructuring and operational liquidity

Annual Revenue: $28,000,000 (down 35% YoY)
Net Income: -$4,200,000
DTI: 1.82
Credit Score: 540
Years in Business: 7

Risk indicators:
- 3 prior loan defaults (2021, 2022, 2023)
- Active judgment from supplier — $1.8M
- Tax lien from IRS — $680,000
- Late payments on 4 credit facilities (60+ days)
- Vendor on credit hold for non-payment
- Management turnover: 3 CFOs in 2 years
Collateral: Inventory and AR $6,100,000 (heavily depreciated).
""",
    ),
    EvalDocument(
        doc_id="EVAL-015",
        category="loan_application",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Startup with no revenue and fraud indicator",
        document_text="""
SMALL BUSINESS LOAN APPLICATION
Borrower: Apex Global Ventures LLC
Date: 2024-03-18
Loan Amount: $850,000
Loan Purpose: Business operations

Annual Revenue: $0
Net Income: -$620,000
DTI: N/A
Credit Score: 490
Years in Business: 0.3

Risk indicators:
- No revenue, no customers, no product in market
- Personal bankruptcy (principal): discharged 2021
- Previous business: dissolved under fraud investigation (2019)
- Credit score reflects 7 collection accounts
- Collateral: Personal vehicle $22,000 — grossly insufficient
""",
    ),
    EvalDocument(
        doc_id="EVAL-016",
        category="financial_statement",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Insolvent company seeking bridge loan",
        document_text="""
BRIDGE LOAN APPLICATION
Borrower: Meridian Energy Solutions Corp
Date: 2024-01-08
Loan Amount: $18,500,000
Loan Purpose: Prevent covenant default on existing senior facilities

Annual Revenue: $45,000,000 (down 40% YoY)
Net Income: -$9,800,000
DTI: 2.41
Credit Score: 512
Years in Business: 11

Risk indicators:
- Existing covenant defaults on 2 senior facilities
- Going concern language in auditor's report (FY2023)
- Pending creditor litigation — $14M in claims
- Asset sale process underway (non-core assets)
- SEC inquiry into revenue recognition practices
- Cash runway: estimated 45 days
Collateral: Remaining assets $8,200,000 (contested by senior creditors).
""",
    ),
    EvalDocument(
        doc_id="EVAL-017",
        category="loan_application",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Serial defaulter with active liens",
        document_text="""
COMMERCIAL LOAN APPLICATION
Borrower: Riverside Construction LLC
Date: 2024-04-10
Loan Amount: $2,200,000
Loan Purpose: Equipment and working capital

Annual Revenue: $5,400,000
Net Income: -$380,000
DTI: 0.88
Credit Score: 558
Years in Business: 6

Risk indicators:
- 2 mechanic's liens filed against properties (total $940,000)
- 1 active judgment — bank seizure of AR (2023)
- Credit score history: multiple 90-day delinquencies
- Related-party loans to principals: $320,000 undisclosed until audit
- OSHA violations: 3 citations, 1 unresolved
- Prior SBA loan: classified as loss (2022)
""",
    ),
    EvalDocument(
        doc_id="EVAL-018",
        category="contract",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Real estate speculator, overleveraged",
        document_text="""
REAL ESTATE DEVELOPMENT LOAN APPLICATION
Borrower: SkyLine Development Partners LLC
Date: 2024-03-22
Loan Amount: $24,000,000
Loan Purpose: Mixed-use tower development

Annual Revenue: $3,200,000 (management fees only)
Net Income: -$1,400,000
DTI: 3.12
Credit Score: 601
Years in Business: 3

Risk indicators:
- No prior projects of this scale completed
- LTV: 96% (collateral: undeveloped land $25M — highly speculative)
- No pre-sales, no anchor tenants committed
- Principal has 2 prior real estate ventures that defaulted
- Construction cost overrun risk: no fixed-price GC contract
- Market: Oversupply in target submarket (downtown office/residential)
Collateral: Land only — no guarantees, no construction completion bond.
""",
    ),
    EvalDocument(
        doc_id="EVAL-019",
        category="loan_application",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Crypto company, unregulated, near-insolvent",
        document_text="""
WORKING CAPITAL LOAN APPLICATION
Borrower: TokenFi Exchange Corp
Date: 2024-02-12
Loan Amount: $7,500,000
Loan Purpose: Customer withdrawal reserves and operational costs

Annual Revenue: $1,200,000 (down 89% YoY)
Net Income: -$5,600,000
DTI: 4.10
Credit Score: 523
Years in Business: 2

Risk indicators:
- Crypto exchange subject to 3 regulatory investigations (FinCEN, SEC, CFTC)
- Customer funds commingling allegation — internal audit pending
- Prior CEO charged with securities fraud (2023, separate entity)
- No FDIC insurance, no regulatory license in US
- Counterparties: sanctioned-country transactions flagged
- 6 wire transfers to high-risk jurisdictions flagged by BSA
""",
    ),
    EvalDocument(
        doc_id="EVAL-020",
        category="loan_application",
        expected_decision="reject",
        expected_score_range=(80, 100),
        description="Shell company, suspected fraud",
        document_text="""
COMMERCIAL LOAN APPLICATION
Borrower: Global Opportunities Investment LLC
Date: 2024-04-05
Loan Amount: $5,000,000
Loan Purpose: Investment opportunities (unspecified)

Annual Revenue: $14,000,000 (unverified — no audited statements provided)
Net Income: $2,800,000 (self-reported)
DTI: Unknown
Credit Score: 582
Years in Business: 1

Risk indicators:
- No audited financial statements — refused to provide
- No verifiable business operations or physical address
- Beneficial ownership: 4 layers of offshore holding companies
- Revenue source: undisclosed international transactions
- Similar entity name flagged in FinCEN suspicious activity report (2023)
- No tax returns provided
- Loan purpose: vague, no business plan submitted
- Collateral: Foreign real estate — unverifiable
""",
    ),
]
