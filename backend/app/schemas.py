from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

StepStatus = Literal["proposed", "blocked", "ready"]

class ProjectPlanRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    goal: str = Field(min_length=10, max_length=5000)
    repository_urls: list[HttpUrl] = Field(default_factory=list, max_length=30)
    constraints: list[str] = Field(default_factory=list, max_length=50)
    prioritize_free_tools: bool = True

class PlanStep(BaseModel):
    id: str
    title: str
    description: str
    status: StepStatus = "proposed"
    needs_approval: bool = False

class ProjectPlanResponse(BaseModel):
    project_name: str
    summary: str
    status: Literal["proposed"] = "proposed"
    assumptions: list[str]
    steps: list[PlanStep]
    evidence_policy: str
