"""Base module – admin-ui view configuration.

System / admin screens: Users, Companies, Partners, ir_* objects.

Note: this static dictionary is a legacy hint format that pre-dates the
registry-driven `GET /api/base/ui-config` builder. The Admin UI catch-all
routes (`[module]/[model]`) read the dynamic config; this file is kept for
parity and any tooling that imports `view_config` declared in the module
manifest.
"""
from __future__ import annotations

UI_CONFIG = {
    "base.user": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Full name"},
                {"key": "email",         "label": "Email"},
                {"key": "is_active",     "label": "Active"},
                {"key": "is_superadmin", "label": "Superadmin"},
                {"key": "language",      "label": "Language"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",     "label": "Full name", "type": "text",  "required": True},
                {"key": "email",    "label": "Email",     "type": "email", "required": True},
                {"key": "password", "label": "Password",  "type": "text"},
                {"key": "language", "label": "Language",  "type": "select",
                 "options": [
                     {"value": "en", "label": "English"},
                     {"value": "pl", "label": "Polski"},
                 ]},
                {"key": "timezone", "label": "Time zone", "type": "text"},
                {"key": "is_active", "label": "Active",   "type": "boolean"},
            ],
        },
    },

    "base.company": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Name"},
                {"key": "currency_code", "label": "Currency"},
                {"key": "country_code",  "label": "Country"},
                {"key": "city",          "label": "City"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",          "label": "Name",         "type": "text",  "required": True},
                {"key": "currency_code", "label": "Currency",     "type": "text"},
                {"key": "country_code",  "label": "Country",      "type": "text"},
                {"key": "vat",           "label": "VAT number",   "type": "text"},
                {"key": "email",         "label": "Email",        "type": "email"},
                {"key": "phone",         "label": "Phone",        "type": "tel"},
                {"key": "street",        "label": "Street",       "type": "text"},
                {"key": "city",          "label": "City",         "type": "text"},
                {"key": "zip_code",      "label": "Postal code",  "type": "text"},
            ],
        },
    },

    "base.partner": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",       "label": "Name"},
                {"key": "email",      "label": "Email"},
                {"key": "phone",      "label": "Phone"},
                {"key": "city",       "label": "City"},
                {"key": "is_company", "label": "Company"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",         "label": "Name",        "type": "text",  "required": True},
                {"key": "email",        "label": "Email",       "type": "email"},
                {"key": "phone",        "label": "Phone",       "type": "tel"},
                {"key": "mobile",       "label": "Mobile",      "type": "tel"},
                {"key": "street",       "label": "Street",      "type": "text"},
                {"key": "city",         "label": "City",        "type": "text"},
                {"key": "zip_code",     "label": "Postal code", "type": "text"},
                {"key": "country_code", "label": "Country",     "type": "text"},
                {"key": "is_company",   "label": "Company",     "type": "boolean"},
                {"key": "vat",          "label": "VAT number",  "type": "text"},
            ],
        },
    },

    "base.ir-config-param": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "key",         "label": "Key"},
                {"key": "value",       "label": "Value"},
                {"key": "description", "label": "Description"},
            ],
        },
        "form": {
            "fields": [
                {"key": "key",         "label": "Key",         "type": "text", "required": True},
                {"key": "value",       "label": "Value",       "type": "text"},
                {"key": "description", "label": "Description", "type": "textarea"},
            ],
        },
    },

    "base.ir-cron": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",            "label": "Name"},
                {"key": "interval_number", "label": "Every"},
                {"key": "interval_type",   "label": "Unit"},
                {"key": "is_active",       "label": "Active"},
                {"key": "next_call",       "label": "Next run"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",            "label": "Name",     "type": "text", "required": True},
                {"key": "model_name",      "label": "Model",    "type": "text"},
                {"key": "function_name",   "label": "Function", "type": "text"},
                {"key": "interval_number", "label": "Every",    "type": "number"},
                {"key": "interval_type",   "label": "Unit",     "type": "select",
                 "options": [
                     {"value": "minutes", "label": "Minutes"},
                     {"value": "hours",   "label": "Hours"},
                     {"value": "days",    "label": "Days"},
                     {"value": "weeks",   "label": "Weeks"},
                 ]},
                {"key": "is_active",       "label": "Active",   "type": "boolean"},
            ],
        },
    },
}
