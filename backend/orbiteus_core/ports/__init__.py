"""Outbound/inbound integration ports (telephony, mailbox, ERP, …)."""

from orbiteus_core.ports.ifs_inbound import IfsInboundPort, IfsShipmentEvent
from orbiteus_core.ports.mailbox import EmailMessage, MailboxPort
from orbiteus_core.ports.telephony import CallEvent, TelephonyPort

__all__ = [
    "CallEvent",
    "EmailMessage",
    "IfsInboundPort",
    "IfsShipmentEvent",
    "MailboxPort",
    "TelephonyPort",
]
