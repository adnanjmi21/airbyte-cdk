#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#


import json
import re
from typing import Union

from jsonschema import RefResolver
from pydantic import BaseModel, Field

from .streams import DEFAULT_START_DATE, ReportGranularity


class OauthCredSpec(BaseModel):
    class Config:
        title = "OAuth"

    auth_type: str = Field(default="oauth2.0", const=True, order=0)

    app_id: str = Field(title="App ID", description="The App ID applied by the developer.", airbyte_secret=True)

    secret: str = Field(title="Secret", description="The private key of the developer's application.", airbyte_secret=True)

    access_token: str = Field(title="Access Token", description="The long-term authorized access token.", airbyte_secret=True)


class SandboxEnvSpec(BaseModel):
    class Config:
        title = "Sandbox"

    auth_type: str = Field(default="sandbox_access_token", const=True, order=0)

    # it is string because UI has the bug https://github.com/airbytehq/airbyte/issues/6875
    advertiser_id: str = Field(
        title="Advertiser ID", description="The Advertiser ID which generated for the developer's Sandbox application."
    )

    access_token: str = Field(title="Access Token", description="The long-term authorized access token.", airbyte_secret=True)


class SourceTiktokMarketingSpec(BaseModel):
    class Config:
        title = "TikTok Marketing Source Spec"

    credentials: Union[OauthCredSpec, SandboxEnvSpec] = Field(title="Authentication *", order=0, default={}, type="object")

    start_date: str = Field(
        title="Start Date *",
        default=DEFAULT_START_DATE,
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
        description="The Start Date in format: YYYY-MM-DD. Any data before this date will not be replicated."
        "If this parameter is not set, all data will be replicated.",
        order=1,
    )

    report_granularity: str = Field(
        title="Report Granularity *",
        description="Grouping of your reports based on time. Lifetime will have no grouping. This option is used for reports' streams only.",
        default=ReportGranularity.default().value,
        enum=[g.value for g in ReportGranularity],
        order=2,
    )

    @classmethod
    def change_format_to_oneOf(cls, schema: dict) -> dict:
        new_schema = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                value = cls.change_format_to_oneOf(value)
            if key == "anyOf":
                new_schema["oneOf"] = value
            else:
                new_schema[key] = value
        return new_schema

    @staticmethod
    def resolve_refs(schema: dict) -> dict:
        json_schema_ref_resolver = RefResolver.from_schema(schema)
        str_schema = json.dumps(schema)
        for ref_block in re.findall(r'{"\$ref": "#\/definitions\/.+?(?="})"}', str_schema):
            ref = json.loads(ref_block)["$ref"]
            str_schema = str_schema.replace(ref_block, json.dumps(json_schema_ref_resolver.resolve(ref)[1]))
        pyschema = json.loads(str_schema)
        del pyschema["definitions"]
        return pyschema

    @classmethod
    def schema(cls) -> dict:
        """we're overriding the schema classmethod to enable some post-processing"""
        schema = super().schema()
        schema = cls.change_format_to_oneOf(schema)
        return cls.resolve_refs(schema)


class CompleteOauthOutputSpecification(BaseModel):
    access_token: str = Field(path_in_connector_config=["credentials", "access_token"])


class CompleteOauthServerInputSpecification(BaseModel):
    app_id: str = Field()
    secret: str = Field()


class CompleteOauthServerOutputSpecification(BaseModel):
    app_id: str = Field(path_in_connector_config=["credentials", "app_id"])
    secret: str = Field(path_in_connector_config=["credentials", "secret"])
