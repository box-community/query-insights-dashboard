# Contract analytics dashboard with query insights

A minimal, runnable reference app that aggregates contract metadata from Box
into dashboard metrics — counts, sums, averages, and grouped breakdowns —
without listing every file.

It uses the
[Box Query Insights API](https://developer.box.com/guides/query/insights)
to filter items with the same predicate syntax as
[Box query](https://developer.box.com/guides/query/box-query), optionally group
results, and request metrics such as `count`, `sum`, `avg`, `min`, and `max` in
a single API call. A Python client authenticates with Client Credentials
Grant (CCG), then prints a console report you can adapt for a web dashboard or
BI export.

This is the companion repository to the tutorial
**[Build a contract analytics dashboard with query insights](https://developer.box.com/tutorials/query-insights-dashboard)**.

## What it does

| Capability | How |
| --- | --- |
| Authenticate with CCG | `POST /oauth2/token` (enterprise subject) with `box-sdk-gen` |
| Count matching contracts | `POST /2.0/query/insights` with empty `metrics` → `totalResultCount` |
| Average / min / max contract value | Named `avg`, `min`, `max` metrics on a float field |
| Top contract types by value | `group_by` + `sum` / `count` metrics |
| Scope to a folder | `ancestors` set to a department or program root |

## Project layout

```
query-insights-dashboard/
├── app.py                 # CCG auth + query insights dashboard
├── make_sample_pdfs.py    # Regenerates sample contract PDFs
├── sample-contract-*.pdf
├── requirements.txt
├── .env.example
└── .gitignore
```

## Prerequisites

- **Python 3.11+**
- A free [Box developer account](https://account.box.com/signup/developer) with
  access to the [Developer Console](https://cloud.app.box.com/developers/console)
- A **Client Credentials Grant (CCG)** Platform App with the scope
  **Read and write all files and folders stored in Box**, and the app
  **authorized** for your enterprise in the Developer Console and
  [Admin Console](https://app.box.com/master/settings/openbox)
- Content in Box tagged with a metadata template. This sample assumes a
  `sales` template with at least:
  - `contractType` (text or enum)
  - `contractValue` (float)

## Setup

1. **Clone and enter the project**

   ```bash
   git clone <your-fork-url> query-insights-dashboard
   cd query-insights-dashboard
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Prepare sample metadata in Box** (if you do not already have tagged
   contracts):

   Create a template with `contractType` and `contractValue`, a folder to scope
   results, sample files, and apply the template. Example with the Box CLI:

   ```bash
   box metadata template create --name "Sales Contracts" \
     --fields "contractType:text,contractValue:float"
   box folder create --name "Sales Contracts"
   # Create sample files and apply the template to your folder
   ```

4. **Configure credentials**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in values from the Developer Console and your template:

   ```bash
   BOX_CLIENT_ID=your_client_id
   BOX_CLIENT_SECRET=your_client_secret
   BOX_ENTERPRISE_ID=your_enterprise_id
   FOLDER_ID=your_folder_id
   TEMPLATE_KEY=your_template_key
   TEMPLATE_REF=your_template_ref
   FIELD_CONTRACT_TYPE=your_contract_type_field
   FIELD_CONTRACT_VALUE=your_contract_value_field
   ```

   Use a template reference of the form `enterprise_<id>:<templateKey>` (for
   example `enterprise_12345678:sales`). Field paths look like
   `enterprise_12345678:sales:contractType`.

   > **Never commit `.env`.** It is already in `.gitignore`.

## Run

```bash
python app.py
```

The script authenticates, calls query insights for count / value stats / grouped
breakdowns, and prints a short console report.

## Try it

1. **Count contracts** that match your template in the scoped folder (empty
   `metrics` returns the default `totalResultCount`):

   ```bash
   curl -X POST "https://api.box.com/2.0/query/insights" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "query": {
         "predicate": "EXISTS(:templateArg)",
         "params": { "templateArg": "enterprise_12345678:sales" },
         "ancestors": [{ "id": "987654321", "type": "folder" }]
       },
       "metrics": {}
     }'
   ```

2. **Compute value stats** — average, minimum, and maximum deal size for a date
   range — by requesting named `avg` / `min` / `max` metrics in one call.

3. **Group for a chart** — add `group_by` on `contractType` with a
   `bucket_limit` (default 5, max 10). Top buckets come back as `group`
   entries; remaining groups roll into an `other` entry.

> Query insights applies filters first, then grouping, then metrics. It does
> **not** return individual items. For file-level drill-down, use
> [Box query](https://developer.box.com/guides/query/box-query) or the
> [metadata query API](https://developer.box.com/guides/metadata/queries) with
> the same predicates.

## How it works

Access tokens are minted **server-side** with CCG and never exposed beyond the
script. Each dashboard call posts a JSON body to `/2.0/query/insights` with a
`query` (predicate, params, optional `ancestors` / `group_by`) and a `metrics`
map. Responses contain `overall`, `group`, and optionally `other` insight
entries — read metric values from `metrics`, and for groups use `key[0]` as the
label.

Only one `group_by` field is supported per request. Avoid high-cardinality
fields; cardinality above 10,000 can cause errors.

## Security notes

- Keep the client secret, enterprise ID, and access token out of the browser
  and out of git.
- Prefer the least privilege your reporting needs; authorize CCG only for the
  enterprise that owns the content.
- Scope queries with `ancestors` so each team dashboard only sees its folder
  tree.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `404 INSTANCE_NOT_FOUND` | Confirm `enterprise_<id>:<templateKey>` matches your template. |
| `403 FORBIDDEN` | Verify app scopes and that the service account can read the folder. |
| `400 BAD_REQUEST` | Check placeholder names match `params` keys and field types. |
| `429 RATE_LIMIT_EXCEEDED` | Back off and cache dashboard results instead of calling on every page load. |

For the full parameter reference, response fields, and additional examples, see
[Query insights](https://developer.box.com/guides/query/insights).

## License

[MIT](./LICENSE)
