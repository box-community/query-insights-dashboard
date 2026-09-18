#!/usr/bin/env python3
"""Query Insights helpers that power the contract analytics dashboard."""

from __future__ import annotations

from box_sdk_gen import (
    BoxClient,
    CreateQueryInsightV2026R0Query,
    QueryAncestorReferenceV2026R0,
    QueryInsightEntryV2026R0TypeField,
    QueryInsightsGroupByV2026R0,
    QueryInsightsMetricDefinitionV2026R0,
    QueryInsightsMetricDefinitionV2026R0TypeField,
    QueryInsightsV2026R0,
)


def overall_entry(result: QueryInsightsV2026R0):
    return next(
        entry
        for entry in result.insights
        if entry.type == QueryInsightEntryV2026R0TypeField.OVERALL
    )


def count_contracts(client: BoxClient, template_ref: str, folder_id: str) -> float:
    result = client.query.create_query_insight_v2026_r0(
        CreateQueryInsightV2026R0Query(
            predicate="EXISTS(:templateArg)",
            params={"templateArg": template_ref},
            ancestors=[QueryAncestorReferenceV2026R0(id=folder_id, type="folder")],
        ),
        {},
    )
    metric = overall_entry(result).metrics["totalResultCount"]
    return metric.values[metric.type]


def contract_value_stats(
    client: BoxClient,
    template_ref: str,
    folder_id: str,
    value_field: str,
    start_date: str,
    end_date: str,
) -> dict:
    result = client.query.create_query_insight_v2026_r0(
        CreateQueryInsightV2026R0Query(
            predicate=(
                "EXISTS(:templateArg) AND "
                "box:item:created_at >= :startDate AND "
                "box:item:created_at < :endDate"
            ),
            params={
                "templateArg": template_ref,
                "startDate": start_date,
                "endDate": end_date,
            },
            ancestors=[QueryAncestorReferenceV2026R0(id=folder_id, type="folder")],
        ),
        {
            "avgContractValue": QueryInsightsMetricDefinitionV2026R0(
                type=QueryInsightsMetricDefinitionV2026R0TypeField.AVG,
                field=value_field,
            ),
            "minContractValue": QueryInsightsMetricDefinitionV2026R0(
                type=QueryInsightsMetricDefinitionV2026R0TypeField.MIN,
                field=value_field,
            ),
            "maxContractValue": QueryInsightsMetricDefinitionV2026R0(
                type=QueryInsightsMetricDefinitionV2026R0TypeField.MAX,
                field=value_field,
            ),
        },
    )
    return {
        alias: metric.values[metric.type]
        for alias, metric in overall_entry(result).metrics.items()
    }


def top_contract_types(
    client: BoxClient,
    template_ref: str,
    folder_id: str,
    type_field: str,
    value_field: str,
    bucket_limit: int = 5,
) -> list[dict]:
    result = client.query.create_query_insight_v2026_r0(
        CreateQueryInsightV2026R0Query(
            predicate="EXISTS(:templateArg)",
            params={"templateArg": template_ref},
            ancestors=[QueryAncestorReferenceV2026R0(id=folder_id, type="folder")],
            group_by=[
                QueryInsightsGroupByV2026R0(
                    field=type_field, bucket_limit=bucket_limit
                )
            ],
        ),
        {
            "totalContractValue": QueryInsightsMetricDefinitionV2026R0(
                type=QueryInsightsMetricDefinitionV2026R0TypeField.SUM,
                field=value_field,
            ),
            "countByType": QueryInsightsMetricDefinitionV2026R0(
                type=QueryInsightsMetricDefinitionV2026R0TypeField.COUNT,
                field=type_field,
            ),
        },
    )

    groups = []
    for entry in result.insights:
        if entry.type == QueryInsightEntryV2026R0TypeField.GROUP:
            groups.append(
                {
                    "contract_type": entry.key[0],
                    "total_value": entry.metrics["totalContractValue"].values["sum"],
                    "count": entry.metrics["countByType"].values["count"],
                }
            )
        elif entry.type == QueryInsightEntryV2026R0TypeField.OTHER:
            groups.append(
                {
                    "contract_type": "Other",
                    "count": entry.metrics["totalCountBeyondTopGroups"].values["count"],
                }
            )
    return groups
