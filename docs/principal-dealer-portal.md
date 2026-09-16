# Principal Portal, Dealers Portal, and AutoDS interconnection

AutoDS can run as a **Dealer** site or a **Principal** site. Both share the same DocTypes. Desk workspaces:

- **Principal Portal** — dealer staff monitor orders and warranty claims with their OEM/distributor
- **Dealers Portal** — principal staff monitor the dealer network

A dealer without AutoDS can still log into a principal site at `/dealers-portal` (role **Dealer Portal User**).

## Site identity

Open **Principal Dealer Settings**:

1. Set **Site Role** to `Dealer` or `Principal`
2. Set **Party Code** — this site's identity. It must match the counterpart master `code` (Dealer code on the principal site, Principal code on the dealer site)
3. On a dealer site, set **Default Principal** when users are not mapped individually

Map users:

- Dealer site: User **Principal** (`custom_principal`) + role `Principal Portal User`
- Principal site staff: role `Dealers Portal User`
- Dealer logging into a principal site: User **Dealer** (`custom_dealer`) + role `Dealer Portal User`

## Pairing two AutoDS sites

Documents stay local unless a **Portal Connection** is enabled. Sync is bidirectional REST, not a shared database.

**On the principal site**

1. Site Role = Principal, Party Code = e.g. `TOYOTA-PH`
2. Create a **Dealer** whose **Code** is the dealer's party code (e.g. `DEALER-001`)
3. Create a User with role **Portal Sync User** (no Desk). Generate API Key / API Secret
4. Create a reverse **Portal Connection** later (dealer URL + dealer API key) so confirmations and circulars can flow back

**On the dealer site**

1. Site Role = Dealer, Party Code = `DEALER-001`
2. Create a **Principal** whose **Code** is `TOYOTA-PH`
3. Create a Portal Sync User and API key for the principal to call back
4. **Portal Connection**: Party Type `Principal`, Party = that Principal, Party Code `TOYOTA-PH`, Site URL of the principal AutoDS, API key/secret from step 3 on the principal
5. **Test Connection** — handshake must return the same party code

Repeat the reverse connection on the principal site (Party Type `Dealer`).

## What syncs

| Event | Direction |
| --- | --- |
| Principal Order submit | Dealer → Principal (`upsert_principal_order`) |
| Order confirm / deliver / close / cancel | Principal → Dealer (`update_principal_order_status`) |
| Warranty Claim submit | Dealer → Principal (`upsert_warranty_claim`) |
| Claim review / approve / reject / settle | Principal → Dealer (`update_warranty_claim_status`) |
| Dealer Circular publish | Principal → each connected dealer (`publish_circular`) |

Identity on the wire is `origin_site` + `origin_name` plus `principal_code` / `dealer_code`. Repeat posts update the same remote document. Inbound handlers set a loop guard so the receiving site does not push the same change back.

Failures never block local submit. Check **Portal Sync Log** (`Queued` / `Success` / `Failed`) and **Retry**. An hourly job retries failed outbound logs (up to **Max Sync Retries**).

## What stays local

Purchase Order, Sales Order, Repair Order, Vehicle Unit links, stock, and GL are not replicated. Item rows sync by `item_code`; if the far site has no matching Item, the line is stored as description-only.

Warranty **Bill To** on Repair Order is unchanged. Use **Create → Warranty Claim** on a Repair Order that has warranty lines to open a first-class **Warranty Claim**.

## API

Counterpart calls (token auth: `Authorization: token api_key:api_secret`):

- `autods.principal_portal.api.handshake`
- `autods.principal_portal.api.upsert_principal_order`
- `autods.principal_portal.api.update_principal_order_status`
- `autods.principal_portal.api.upsert_warranty_claim`
- `autods.principal_portal.api.update_warranty_claim_status`
- `autods.principal_portal.api.publish_circular`

Payload is form field `payload` (JSON). Methods require **Portal Sync User** or System Manager.
