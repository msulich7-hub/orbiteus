"""DSV / DB Schenker Connect Booking SOAP types — port of dsv-types.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DsvAddressType = Literal["SHIPPER", "CONSIGNEE", "PICKUP", "DELIVERY", "NOTIFY", "INVOICE"]
DsvPersonType = Literal["COMPANY", "PRIVATE"]
DsvLocationType = Literal["PHYSICAL", "POSTAL"]
DsvBarcodeFormat = Literal["A4", "A5", "A6", "LABEL"]
DsvMeasurementType = Literal["METRIC", "IMPERIAL"]
DsvMeasureUnit = Literal["VOLUME", "LOADING_METERS", "PALLET_SPACE", "PIECES"]


@dataclass
class DsvContactPerson:
    name: str | None = None
    phone: str | None = None
    email: str | None = None


@dataclass
class DsvAddress:
    type: DsvAddressType
    name1: str
    street: str
    postal_code: str
    city: str
    country_code: str
    person_type: DsvPersonType
    location_type: DsvLocationType
    name2: str | None = None
    street2: str | None = None
    schenker_address_id: str | None = None
    vat_no: str | None = None
    customs_id: str | None = None
    phone: str | None = None
    mobile_phone: str | None = None
    email: str | None = None
    contact_person: DsvContactPerson | None = None


@dataclass
class DsvReference:
    number: str
    id: str


@dataclass
class DsvShipmentPosition:
    cargo_desc: str
    package_type: str
    pieces: int
    gross_weight: str
    volume: str
    stackable: bool
    dgr: bool
    length: str | None = None
    width: str | None = None
    height: str | None = None


@dataclass
class DsvPickupDates:
    pick_up_date_from: str
    pick_up_date_to: str


@dataclass
class DsvBarcodeRequest:
    format: DsvBarcodeFormat
    start_pos: int
    separated: bool
    direct_thermal_media: bool = False


@dataclass
class DsvApplicationArea:
    access_key: str
    group_id: int | None = None
    request_id: str | None = None
    user_id: str | None = None


@dataclass
class DsvShippingInformation:
    shipment_positions: list[DsvShipmentPosition]
    volume: str
    gross_weight: str | None = None


@dataclass
class DsvBookingLandRequest:
    application_area: DsvApplicationArea
    submit_booking: bool
    addresses: list[DsvAddress]
    incoterm: str
    incoterm_location: str
    product_code: str
    measurement_type: DsvMeasurementType
    gross_weight: str
    customs_clearance: bool
    indoor_delivery: bool
    neutral_shipping: bool
    special_cargo: bool
    service_type: Literal["D2D"]
    express: bool
    food_related: bool
    heated_transport: bool
    home_delivery: bool
    measure_unit: DsvMeasureUnit
    own_pickup: bool
    pickup_dates: DsvPickupDates
    shipping_information: DsvShippingInformation
    return_barcode_references: bool = False
    barcode_request: DsvBarcodeRequest | None = None
    cargo_description: str | None = None
    measure_unit_volume: str | None = None
    references: list[DsvReference] = field(default_factory=list)
    handling_instructions: str | None = None


@dataclass
class DsvBarcodeReference:
    barcode: str
    barcode_type: str


@dataclass
class DsvBookingResponse:
    booking_id: str
    request_id: str | None = None
    barcode_references: list[DsvBarcodeReference] | None = None
    barcode_document: str | None = None


@dataclass
class DsvConnectCredentials:
    access_key: str
    group_id: int | None = None
    user_id: str | None = None
