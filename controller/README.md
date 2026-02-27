# Redis Format

```
ma:vps:{vps}:{collector}
```

# JSON Format

All incoming JSON blurbs MUST have:

```
{
  "collector": "<string>",
  "ts": <int>,
  "metrics": { ... }
}
```

Some kinds of events might have additional toplevel key (WP):

```
{
  "collector": "<string>",
  "app": "<webapp>",
  "ts": <int>,
  "metrics": { ... }
}
```

# Postgres

```
su - postgres

psql

CREATE USER massaffect WITH PASSWORD 'strongpassword';
CREATE DATABASE massaffect OWNER massaffect;

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    vps TEXT NOT NULL,
    collector TEXT NOT NULL,
    ts BIGINT NOT NULL,
    metrics JSONB NOT NULL
);
```

In order to make `psql` interaction cleaner, create `~/.pgpass` with this format:

```
hostname:port:database:username:password
```

For example:

```
localhost:5432:massaffect:massaffect:yourpassword
```

**NOTE**: Be sure to `chmod 600 ~/.pgpass`, this is *not optional*.

# HTTP Codes Cheatsheet

| Code | Description |
| --- | --- |
| 200 | OK |
| 201 |Created |
| 204 | No Content |
| 301, 308 | Permanent redirect |
| 302, 307 | Temporary redirect |
| 304 |Cache hit |
| 400 | Bad request |
| 401 | Needs login |
| 403 | Forbidden |
| 404 | Not found |
| 409 | Conflict |
| 422 | Validation error |
| 429 | Rate limit |
| 500 | Server broke |
| 502 | Upstream broke |
| 503 | Server busy |
| 504 | Upstream timeout |
