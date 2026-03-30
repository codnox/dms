from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class InventoryItemStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class MovementType(str, Enum):
    IN = "in"
    OUT = "out"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"


class InventoryItemBase(BaseModel):
    item_id: str
    name: str
    serial_number: str
    mac_id: str
    device_type: str
    price: float = Field(default=0, ge=0)
    unit: str = "pcs"
    quantity_on_hand: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=0, ge=0)
    supplier_name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_identifier_rules(self):
        device_type = str(self.device_type or "").strip().lower()
        mac_or_nu_id = str(self.mac_id or "").strip()

        if device_type in {"normal", "set-top box"} and not mac_or_nu_id:
            raise ValueError("MAC ID/NU ID is required for Normal and Set-top Box types")

        return self


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    item_id: Optional[str] = None
    name: Optional[str] = None
    serial_number: Optional[str] = None
    mac_id: Optional[str] = None
    device_type: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    quantity_on_hand: Optional[int] = Field(default=None, ge=0)
    reorder_level: Optional[int] = Field(default=None, ge=0)
    supplier_name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[InventoryItemStatus] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_identifier_rules(self):
        if self.device_type is None:
            return self

        device_type = str(self.device_type or "").strip().lower()
        mac_or_nu_id = str(self.mac_id or "").strip() if self.mac_id is not None else ""

        if device_type in {"normal", "set-top box"} and not mac_or_nu_id:
            raise ValueError("MAC ID/NU ID is required when type is Normal or Set-top Box")

        return self


class PurchaseOrderLineCreate(BaseModel):
    item_inventory_id: str
    quantity_ordered: int = Field(..., ge=1)
    unit_cost: Optional[float] = Field(default=None, ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_name: str
    expected_date: Optional[str] = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.SUBMITTED
    notes: Optional[str] = None
    lines: List[PurchaseOrderLineCreate]


class ReceiptLineCreate(BaseModel):
    item_inventory_id: str
    quantity_received: int = Field(..., ge=1)
    unit_cost: Optional[float] = Field(default=None, ge=0)


class ReceiptCreate(BaseModel):
    notes: Optional[str] = None
    lines: List[ReceiptLineCreate]


class StockAdjustmentCreate(BaseModel):
    item_inventory_id: str
    quantity_change: int
    reason: str


class ExternalInventoryDashboard(BaseModel):
    total_skus: int
    total_units: int
    low_stock_items: int
    pending_purchase_orders: int
    inventory_value: float
