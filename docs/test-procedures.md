# Hybrid-MPlane Test Case Overview

This document provides an overview of Hybrid-MPlane conformance test cases.  
Each test case is defined in its own Markdown file for clarity and modularity.

---

## Test Case Index

| Test Case ID                  | Title                                  | Description |
|-------------------------------|----------------------------------------|-------------|
| [TC-HMP-001](./tc-hmp-001.md) | NETCONF Call Home Establishment | Ensure the O-RU initiates a NETCONF Call Home session to the O-RU Controller using DHCP-discovered configuration. |
| [TC-HMP-002](./tc-hmp-002.md) | Read-Only Data Retrieval (Unfiltered, Filtered, and Config-Only) | Verify that the O-RU exposes operational and configuration data via NETCONF and that the O-RU Controller retrieves and exposes this data using RESTCONF in JSON format. |
| [TC-HMP-003](./tc-hmp-003.md) | NETCONF Sessions Verification | Verify that the O-RU has at least two active NETCONF sessions (one towards the O-RU Controller and another towards the O-DU). |
| [TC-HMP-004](./tc-hmp-004.md) | O-RU Configurability Test (Positive Case) | Verify that the O-RU accepts valid user-plane configuration and that the O-RU Controller applies it via RESTCONF. |

---

## Directory Structure

```
docs/
├── overview.md
├── tc-hmp-001.md
├── tc-hmp-002.md
…
```

---

## Notes

- Each test case follows a common structure including objective, preconditions, steps, expected results, and pass/fail criteria.
- Tests are described from the perspective of the O-RU Controller (e.g., part of the SMO).
- YANG modules and capabilities referenced are based on O-RAN WG4 Section 3.1 and filtered for Hybrid-MPlane applicability.

---

## Configuration Parameters

The following configuration parameters are required for specific test cases:

| Test Case ID | Parameter Name | Description | Default Value |
|--------------|----------------|-------------|---------------|
| TC-HMP-002 | tc_002_mountpoint_name | The mountpoint name used for RESTCONF requests | Depends on implementation |
| TC-HMP-003 | tc_003_mountpoint_name | The mountpoint name used for RESTCONF requests | pynts-o-ru-hybrid |
| TC-HMP-004 | tc_004_mountpoint_name | The mountpoint name used for RESTCONF requests to configure user-plane parameters | pynts-o-ru-hybrid |
