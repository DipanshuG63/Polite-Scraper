from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class BookRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    product_url: HttpUrl
    price_text: str = Field(min_length=1)
    price_gbp: float = Field(ge=0)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(min_length=1)
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: datetime

    def as_json_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["product_url"] = str(self.product_url)
        data["source_page"] = str(self.source_page)
        return data
