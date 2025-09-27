# Additions To API with Sustainable Evolvability In-Mind
These were the changes that we had to incur in order to implement Rate Limiting to our REST API.

### Note:
This iteration expands on the issues addressed in [Iteration 2](../library-api-with-ratelimiting/problems-iteration2.md).

# Pre-requisites

**None**

# Versioning


## Changes to the code

### ./app/requirements.txt
- add an entry for `slowapi` library

### ./app/main.py
- Configure the Limiter for the REST API to use, for example, clients IP address
- Pass the `Limiter` to the routes as needed. Se the example for `./router/authors.py`

### ./app/routers/authors.py
- wrapped the creation of the routes with a `.create_authors_router()` method
- make sure to pass in the `Request` parameter since the limiter requires a `request` or `websocket` parameter explicitly defined.