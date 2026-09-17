<!--
Copyright (C) 2026 EloqData Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# keylane Roadmap

Durable backlog for the keylane Redis-compatible server. Runtime-level items live
in `bycorf/ROADMAP.md`.

- **Phase 2: pipeline command batching / squashing.** Coalesce pipelined commands
  per connection to amortize dispatch and cross-shard hops.
- **Phase 3: `CompactObj` + zero-copy RESP parsing.** Parse requests directly out
  of the recv buffer and store small values inline (Redis-style 0-alloc path).
