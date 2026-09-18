# Contract analytics dashboard with query insights

A minimal, runnable reference app that aggregates contract metadata from Box
into dashboard metrics — counts, sums, averages, and grouped breakdowns —
without listing every file.

Sales, legal, and procurement teams often store contracts in Box with
structured metadata (contract type, value, dates, status). Listing every file
to compute totals is slow and expensive. The
[Box Query Insights API](https://developer.box.com/guides/query/insights)
returns aggregated metrics directly from Box. You filter items with the same
predicate syntax as [Box query](https://developer.box.com/guides/query/box-query),
optionally group results, and request `count`, `sum`, `avg`, `min`, and `max`
in a single API call.

This is the companion repository to the tutorial
**[Build a contract analytics dashboard with query insights](https://developer.box.com/tutorials/query-insights)**.
Clone it, add Client Credentials Grant (CCG) credentials, run the setup
script, and print a console report you can adapt for a web dashboard or BI
export.

Query insights applies filters first, then grouping, then metrics. It does
**not** return individual items. For file-level drill-down, use
[Box query](https://developer.box.com/guides/query/box-query) or the
[metadata query API](https://developer.box.com/guides/metadata/queries).

## What you get

After setup, `python dashboard.py` authenticates with CCG and:

- Counts how many sales contracts match a metadata template in a folder.
- Computes overall average, minimum, and maximum contract values for a date
  range.
- Returns top contract types by document count (and an `other` bucket when
  groups exceed `bucket_limit`).

| Use case | What you compute | Example metrics |
| --- | --- | --- |
| Executive dashboard | Portfolio totals and breakdowns by category | `sum` of contract value grouped by `contractType` |
| Compliance reporting | How many documents match a template in a period | `count` with `box:item:created_at` filters |
| Procurement analytics | Typical and outlier deal sizes | `avg`, `min`, and `max` on a currency field |
| Department scorecards | Metrics scoped to a team folder | `ancestors` set to a department root folder |
| Data quality checks | Volume of tagged content before a migration | Empty `metrics` object for default `totalResultCount` |

## Project layout

```
query-insights-dashboard/
├── box_client.py          # CCG auth
├── reports.py             # Typed Query Insights v2026.0 calls
├── dashboard.py           # Console dashboard report
├── setup_test_data.py     # Creates template, folder, and tagged samples
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

## Prerequisites

- **Python 3.11 or higher**
- A free [Box developer account](https://account.box.com/signup/developer)
  (or an enterprise account with Developer Console access)
- A [Platform App](https://cloud.app.box.com/developers/console) using
  **Client Credentials Grant**
- App scope: **Read and write all files and folders stored in Box**
- The app **authorized** for your enterprise (Developer Console and, for
  enterprise accounts, [Admin Console](https://app.box.com/master/settings/openbox))
- Query insights available on the account (same family as Box query)

You do **not** need an existing metadata template. `setup_test_data.py` creates
a `sales` template with:

- `contractType` (enum: `Sales`, `Renewal`)
- `contractValue` (float)

Query Insights can group on enum fields, not free-text string fields. Grouping
on a string `contractType` returns `400 Invalid query request`.

You can also point the app at an existing template with those field keys (or
change the field env vars to match yours). If a `sales` template already exists
with `contractType` as a string, use a new `TEMPLATE_KEY` instead of reusing it.

## Create and authorize a Box app

1. Open the [Developer Console](https://cloud.app.box.com/developers/console)
   and create a **Custom App** / Platform App.
2. Choose **Server Authentication (Client Credentials Grant)**.
3. On the **Configuration** tab:
   - Enable **Read and write all files and folders stored in Box**.
   - Copy **Client ID**, **Client Secret**, and **Enterprise ID**.
   - Viewing the client secret requires two-factor authentication on your
     Box account.
4. Authorize the app:
   - **Free developer accounts:** authorization usually completes when you
     create the app. If not, use the prompt on the Configuration tab.
   - **Enterprise accounts:** submit the app for admin approval, then an
     admin authorizes it in Admin Console → **Platform** → **Platform Apps**.
   - After you change scopes, **re-authorize** the app.

<Note>
A CCG app authenticates as the app's **service
account**, not your personal Box user. That service account has its own
empty folder tree. The setup script writes sample files there.
</Note>

To see those files in the Box web app, copy the service account email from
Developer Console → your app → **App Details** → **Service Account** and collaborate yourself on
the `Sales Contracts` folder, or open the content as an admin in Content
Manager. If you instead want to query a folder you already own, invite the
service account as a collaborator on that folder and set `FOLDER_ID` to it.

If the app is not authorized you typically see
`unauthorized_client` / "This app is not authorized by the enterprise".

## Setup

1. **Clone and enter the project**

   ```bash
   git clone https://github.com/box-community/query-insights-dashboard.git
   cd query-insights-dashboard
   ```

2. **Create a virtual environment and install dependencies**

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Windows (Command Prompt):

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Install exactly one Box package: `boxsdk`.

3. **Configure credentials**

   ```bash
   cp .env.example .env
   ```

   Fill in at least the first three values from the Developer Console **now**.
   Leave the folder and template placeholders until after the next step (or
   fill them if you already have a tagged folder):

   | Variable | Where to get it |
   | --- | --- |
   | `BOX_CLIENT_ID` | Developer Console → Configuration → OAuth 2.0 Credentials |
   | `BOX_CLIENT_SECRET` | Same page (requires 2FA to view) |
   | `BOX_ENTERPRISE_ID` | Developer Console → General / Configuration, or Admin Console |
   | `FOLDER_ID` | Printed by `setup_test_data.py`, or the folder ID from the Box URL (`…/folder/123`) |
   | `TEMPLATE_KEY` | `sales` unless you use another template key |
   | `TEMPLATE_REF` | `enterprise_<enterpriseId>:<templateKey>` |
   | `FIELD_CONTRACT_TYPE` | `enterprise_<enterpriseId>:<templateKey>:contractType` |
   | `FIELD_CONTRACT_VALUE` | `enterprise_<enterpriseId>:<templateKey>:contractValue` |

   Never commit `.env`. It is listed in `.gitignore`.

4. **Create the template and sample contracts** (skip if you already have
   tagged content):

   ```bash
   python setup_test_data.py
   ```

   The script:

   - Creates enterprise metadata template `sales` with an enum `contractType`
     (or reuses it if it exists).
   - Creates or reuses a folder named **Sales Contracts** in the service
     account root.
   - Uploads four `.txt` sample contracts and applies metadata (skips a file
     if that name already exists in the folder).

   | File | `contractType` | `contractValue` |
   | --- | --- | ---: |
   | Contract 1.txt | Sales | 100000 |
   | Contract 2.txt | Sales | 200000 |
   | Contract 3.txt | Renewal | 150000 |
   | Contract 4.txt | Renewal | 45000 |

   Copy the printed `FOLDER_ID`, `TEMPLATE_REF`, and field paths into `.env`.

   Query insights reads a metadata index that updates shortly after you tag
   content. If a metric returns `0` right after setup, wait about a minute
   and run the dashboard again.

## Run

```bash
python dashboard.py
```

With the sample data above, a successful run looks like:

```text
Contract analytics dashboard

Metric           Value
---------------  -------
Total contracts        4
Average value    123,750
Minimum value     45,000
Maximum value    200,000

Top contract types
Type     Total value  Count
-------  -----------  -----
Sales        300,000      2
Renewal      195,000      2
```

Buckets are ordered by document count descending, so group order varies with
your own data.

`dashboard.py` filters value stats to items created between
`2020-01-01T00:00:00Z` and `2030-01-01T00:00:00Z`. Change those dates in
`print_contract_dashboard` if you need a different window.

## Use your own template and folder

You do not have to run `setup_test_data.py`. Point `.env` at any folder the
service account can read and any template that has an enum type field and a
numeric value field:

```bash
TEMPLATE_KEY=your_template_key
TEMPLATE_REF=enterprise_12345678:your_template_key
FIELD_CONTRACT_TYPE=enterprise_12345678:your_template_key:contractType
FIELD_CONTRACT_VALUE=enterprise_12345678:your_template_key:contractValue
FOLDER_ID=987654321
```

Invite the service account to that folder if it does not already own it.
Keep `ancestors` in the queries so metrics stay scoped to that tree.

## How the API calls work

`BoxCCGAuth` fetches and refreshes the access token. The reports call
`client.query.create_query_insight_v2026_r0`, which sends
`POST https://api.box.com/2.0/query_insights` with the required
`box-version: 2026.0` header. Because the method is generated from the API
spec, you pass typed request objects and read a typed `QueryInsightsV2026R0`
result instead of assembling JSON by hand.

Each request has:

- `query.predicate` — Box query syntax (`EXISTS(:templateArg)`, date
  comparisons, and so on)
- `query.params` — values for `:placeholders`
- `query.ancestors` — folder scope (`id` + `type: folder`)
- `query.group_by` — optional; one field per request; `bucket_limit` defaults
  to 5 and maxes at 10. Group on an enum field such as `contractType`.
- `metrics` — named metrics (`count`, `sum`, `avg`, `min`, `max`) or `{}`
  for the default `totalResultCount`

Every metric result nests its value under `values`, keyed by the metric type,
so `metric.values[metric.type]` reads the value without hard-coding the type.

Avoid grouping on high-cardinality fields; cardinality above 10,000 can
cause errors.

### Count matching contracts

Empty `metrics` returns `totalResultCount`:

```bash
curl -X POST "https://api.box.com/2.0/query_insights" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "box-version: 2026.0" \
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

The `box-version: 2026.0` header is required. The SDK method sets it for you,
so you only pass it when you call the endpoint directly.

Mint `$ACCESS_TOKEN` with CCG (the Python client does this for you):

```bash
curl -X POST "https://api.box.com/oauth2/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=$BOX_CLIENT_ID" \
  -d "client_secret=$BOX_CLIENT_SECRET" \
  -d "box_subject_type=enterprise" \
  -d "box_subject_id=$BOX_ENTERPRISE_ID"
```

### Overall average, min, and max

Named metrics in one call. Example response shape:

```json
{
  "insights": [
    {
      "key": [],
      "type": "overall",
      "metrics": {
        "avgContractValue": { "type": "avg", "values": { "avg": 45055.5 } },
        "minContractValue": { "type": "min", "values": { "min": 22000 } },
        "maxContractValue": { "type": "max", "values": { "max": 75000 } }
      }
    }
  ]
}
```

### Grouped chart buckets

`group_by` on the `contractType` enum returns `group` entries (top buckets,
ordered by document count descending) and optionally an `other` entry for
the rest.

## Response entry types

| Type | When it appears | How to use it |
| --- | --- | --- |
| `overall` | No `group_by`, or a global metric row | Read values from `metrics` |
| `group` | Top buckets from `group_by` | Use `key[0]` as the group label |
| `other` | Groups outside the top `bucket_limit` | Read `totalCountBeyondTopGroups` for remaining document count |

You cannot customize sort order for grouped buckets.

## Scaling to production

- **Cache dashboard results.** Refresh on a schedule (for example every 15
  minutes or hourly) instead of calling query insights on every page load.
  The SDK already retries `429 RATE_LIMIT_EXCEEDED` and `5xx` responses with
  backoff, so cache to reduce the number of calls rather than adding a retry
  loop of your own.
- **Scope queries with `ancestors`.** Pass department or program folder IDs
  so each team sees only its content and the service account only needs
  access to those trees.
- **Pair insights with Box query for drill-down.** Use insights for tiles
  and charts; call Box query when a user clicks a bucket to load files.
- **Keep secrets server-side.** Do not put the client secret or tokens in
  browser code or git.

## Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Missing required environment variables | `.env` not created or placeholders not replaced | Copy `.env.example` to `.env` and fill CCG plus folder/template values |
| `unauthorized_client` / app not authorized | CCG app not authorized, or scopes changed | Authorize (or re-authorize) in Developer Console / Admin Console |
| `404 INSTANCE_NOT_FOUND` | Wrong template reference | Confirm `enterprise_<id>:<templateKey>` matches the template |
| `403 FORBIDDEN` | Missing scope or inaccessible ancestors | Enable read/write files scope; invite the service account to the folder |
| `400 BAD_REQUEST` / `400 Invalid query request` | Invalid predicate, parameter types, or grouping on a string field | Check placeholder names and field types; `group_by` needs an enum. If you previously created `sales.contractType` as a string, re-run setup and use the printed `FIELD_CONTRACT_TYPE` (often `...:contractTypeEnum`) |
| `429 RATE_LIMIT_EXCEEDED` | Too many requests for the enterprise | Cache dashboard results; the SDK already retries with backoff |
| Metrics return `0` | Index lag, wrong folder, or untagged files | Wait a minute after tagging; confirm `FOLDER_ID` and template fields |
| Cannot find **Sales Contracts** in box.com | Files live on the **service account**, not your user | Use the service account email / Content Manager, or collaborate yourself |
| Duplicate sample files | Older setup uploaded without skipping | Current setup skips existing names; delete extras in Box if needed |
| `KeyError` / missing metric | Field path does not match the template | Compare `FIELD_*` env vars to the printed `setup_test_data.py` output |

For the full parameter reference, response fields, and additional examples,
see [Query insights](https://developer.box.com/guides/query/insights).

Related guides:

- [Query insights](https://developer.box.com/guides/query/insights)
- [Box query](https://developer.box.com/guides/query/box-query)
- [Client Credentials Grant](https://developer.box.com/guides/authentication/client-credentials/)
- [Metadata fields](https://developer.box.com/guides/metadata/fields/index)
- [Customizing metadata templates](https://support.box.com/hc/en-us/articles/360044194033-Customizing-Metadata-Templates)

## License

[MIT](./LICENSE)
