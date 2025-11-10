from uuid import UUID

from pydantic import BaseModel


class ConnectItem(BaseModel):
    id: UUID


class SenderInput(BaseModel):
    dv: int
    fingerprint: str


class TicketCreateData(BaseModel):
    dv: int
    sender: SenderInput
    organization: ConnectItem
    source: ConnectItem
    property: ConnectItem
    details: str


class TicketCreateInput(BaseModel):
    data: TicketCreateData


class TicketPropertyResponse(BaseModel):
    id: UUID


class TicketContactResponse(BaseModel):
    id: UUID


class TicketCreateResponse(BaseModel):
    id: UUID
    number: int | None = None
    client_phone: str | None = None
    property: TicketPropertyResponse | None = None
    contact: TicketContactResponse | None = None
    unit_name: str | None = None
    unit_type: str | None = None
