from typing import Optional
from pydantic import BaseModel, Field


class FinancialMetric(BaseModel):
    name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    fiscal_year: int
    source_section: Optional[str] = None
    source_url: Optional[str] = None


class RiskFactor(BaseModel):
    category: str
    description: str
    supporting_evidence: str
    source_section: str
    source_url: str


class CompanyAnalysis(BaseModel):
    company_name: str
    ticker: str
    fiscal_year: int
    filing_url: str
    financial_metrics: list[FinancialMetric] = Field(default_factory=list)
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    management_outlook: list[str] = Field(default_factory=list)
    key_observations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
