# Schwab API Reference

- Source PDF: `/Users/advaitdarbare/Downloads/Trader API - Individual | Products | Charles Schwab Developer Portal.pdf`
- Generated (UTC): `2026-02-18T06:32:54.278670+00:00`
- Generator: `PYTHONPATH=. python3 scripts/generate_schwab_reference.py`
- Notes: Market Data endpoints are parsed from the PDF. Trader endpoints are listed from implemented integration scope.

## Market Data Endpoints (from PDF)

| Method | Path | Summary | Found in PDF text |
|---|---|---|---|
| `GET` | `/quotes` | Quotes by comma-separated symbols | yes |
| `GET` | `/{symbol_id}/quotes` | Quote for a single symbol | yes |
| `GET` | `/chains` | Option chain for a symbol | yes |
| `GET` | `/expirationchain` | Option expirations for a symbol | yes |
| `GET` | `/pricehistory` | OHLCV price history | yes |
| `GET` | `/movers/{symbol_id}` | Top movers for an index | yes |
| `GET` | `/markets` | Market hours for multiple markets | yes |
| `GET` | `/markets/{market_id}` | Market hours for one market | yes |
| `GET` | `/instruments` | Instrument lookup by symbols/projection | yes |
| `GET` | `/instruments/{cusip_id}` | Instrument lookup by CUSIP | yes |

## Trader Endpoints (implemented)

| Method | Path | Summary |
|---|---|---|
| `GET` | `/accounts/{accountNumber}/orders` | Orders for one account |
| `POST` | `/accounts/{accountNumber}/orders` | Place order |
| `GET` | `/accounts/{accountNumber}/orders/{orderId}` | Order by ID |
| `DELETE` | `/accounts/{accountNumber}/orders/{orderId}` | Cancel order |
| `PUT` | `/accounts/{accountNumber}/orders/{orderId}` | Replace order |
| `GET` | `/orders` | Orders for all accounts |
| `POST` | `/accounts/{accountNumber}/previewOrder` | Preview order |
| `GET` | `/accounts/{accountNumber}/transactions` | Transactions list |
| `GET` | `/accounts/{accountNumber}/transactions/{transactionId}` | Transaction by ID |
| `GET` | `/userPreference` | User preferences |

## Tool to Output Contracts

| Tool | Source | Endpoint | Output fields (projected) |
|---|---|---|---|
| `get_analyst_ratings` | `finviz` | `ratings scrape` | `symbol, ratings[].date, ratings[].analyst, ratings[].action, ratings[].rating` |
| `get_company_news` | `finviz` | `company news scrape` | `symbol, news[].date, news[].headline, news[].source` |
| `get_company_overview` | `finviz` | `company overview scrape` | `symbol, company, sector, industry, market_cap, pe ...` |
| `get_company_profile` | `finviz` | `company profile scrape` | `symbol, company, sector, industry, market_cap, pe ...` |
| `get_historical_prices` | `schwab_market_data` | `GET /pricehistory` | `symbol, date, open, high, low, close ...` |
| `get_insider_trades` | `finviz` | `insider trades scrape` | `symbol, insider_trades[].date, insider_trades[].insider, insider_trades[].transaction` |
| `get_market_hours` | `schwab_market_data` | `GET /markets` | `market, product, is_open, date, session_hours` |
| `get_market_movers` | `schwab_market_data` | `GET /movers/{symbol_id}` | `index, sort, movers[].symbol, movers[].last_price, movers[].change` |
| `get_quote` | `schwab_market_data` | `GET /quotes` | `symbol, price, change, percent_change, volume, open ...` |
| `get_stock_news` | `alpaca_news` | `news endpoint` | `headline, source, url, timestamp, summary, symbols` |

## PDF Schema Names (extracted)

- `Bond`
- `FundamentalInst`
- `Instrument`
- `InstrumentResponse`
- `Hours`
- `Interval`
- `Screener`
- `Candle`
- `CandleList`
- `EquityResponse`
- `QuoteError`
- `ExtendedMarket`
- `ForexResponse`
- `Fundamental`
- `FutureOptionResponse`
- `FutureResponse`
- `IndexResponse`
- `MutualFundResponse`
- `OptionResponse`
- `QuoteEquity`
- `QuoteForex`
- `QuoteFuture`
- `QuoteFutureOption`
- `QuoteIndex`
- `QuoteMutualFund`
- `QuoteOption`
- `QuoteRequest`
- `QuoteResponse`
- `QuoteResponseObject`
- `ReferenceEquity`
- `ReferenceForex`
- `ReferenceFuture`
- `ReferenceFutureOption`
- `ReferenceIndex`
- `ReferenceMutualFund`
- `ReferenceOption`
- `RegularMarket`
- `AssetMainType`
- `EquityAssetSubType`
- `MutualFundAssetSubType`
- `ContractType`
- `SettlementType`
- `ExpirationType`
- `FundStrategy`
- `ExerciseType`
- `DivFreq`
- `QuoteType`
- `ErrorResponse`
- `Error`
- `ErrorSource`
- `OptionChain`
- `OptionContractMap`
- `Underlying`
- `OptionDeliverables`
- `OptionContract`
- `ExpirationChain`
- `Expiration`
