"""Pydantic schemas for structured meeting output."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class ActionItem(BaseModel):
    task: str
    owner: str  # person name or "unassigned"
    confidence: Literal["high", "medium", "low"]
    needs_clarification: bool
    evidence: str  # quote from the original notes
    category: Literal["committed", "suggested", "risk_flag"]


class OpenQuestion(BaseModel):
    question: str
    context: str
    raised_by: Optional[str] = None


class MeetingOutput(BaseModel):
    summary: str
    action_items: list[ActionItem]
    open_questions: list[OpenQuestion]
