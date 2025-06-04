# Hybrid-MPlane Test Procedure: Read-Only Data Retrieval (Unfiltered, Filtered, and Config-Only)

## Test Case ID
TC-HMP-002

## Title
Verify that the O-RU exposes operational and configuration data via NETCONF and that the O-RU Controller retrieves and exposes this data using RESTCONF in JSON format.

## Objective
To confirm that the O-RU supports NETCONF `get` and `get-config` operations for unfiltered and subtree-filtered retrievals, and that the O-RU Controller makes this data available via RESTCONF in JSON format.

## Scope
This test covers three types of read-only retrievals from the O-RU Controller:
1. Full data tree (unfiltered)
2. Subtree-filtered data
3. Configuration-only data (i.e., read-write nodes)

---

## Preconditions
- A NETCONF session between the O-RU and the O-RU Controller is active.
- The O-RU supports standard `get` and `get-config` operations.
- The O-RU Controller exposes data via RESTCONF in JSON format.
- The test environment supports making RESTCONF requests to the controller.

---

## Test Steps

### Step 1: Unfiltered Data Retrieval
1. Send a RESTCONF request without any filter to retrieve the full available data tree.
2. Observe the JSON response and verify that it includes both operational and configuration data.

### Step 2: Subtree-Filtered Retrieval
3. Send a RESTCONF request using a subtree filter to target a specific portion of the data (e.g., software version or inventory information).
4. Confirm that the JSON response includes only the specified subtree.

### Step 3: Configuration-Only Retrieval
5. Send a RESTCONF request to retrieve only the configuration data (i.e., read-write nodes).
6. Confirm that the response excludes operational state nodes.

---

## Expected Result
- All RESTCONF requests return successful responses (e.g., HTTP 200), with one exception noted below.
- The unfiltered request returns the full data tree, or a "too-big" error (HTTP 413 or equivalent) if the data is too large for the implementation to handle.
- The filtered request returns only the intended subtree.
- The config-only request excludes operational data.

---

## Pass Criteria
- JSON responses match expectations in terms of content and structure.
- Filtered and config-only views correctly reflect the O-RU's YANG model.
- No errors or protocol violations occur.

## Fail Criteria
- RESTCONF returns HTTP errors or unexpected/malformed JSON.
- Filtered response includes extra or unrelated data.
- Config-only response includes read-only operational nodes.

---

## Postconditions
- NETCONF session remains active and usable for further tests.
- JSON outputs may be archived as test artifacts.

---

## Test Observables and Artifacts

| Artifact | Description |
|----------|-------------|
| **Unfiltered JSON** | Full O-RU data tree as exposed via RESTCONF |
| **Filtered JSON**   | Targeted subtree data retrieved via filter |
| **Config-Only JSON**| Read-write configuration data only |
| **Timestamps**      | Time of each RESTCONF request and response |
| **Logs (optional)** | Logs from O-RU Controller reflecting NETCONF/RESTCONF flow |

---

## Notes
- Subtree filtering is used for this test; XPath filtering is not required.
- RESTCONF responses are expected in JSON format.
- This test indirectly validates the O-RU's NETCONF support through the O-RU Controller's RESTCONF interface.
- For unfiltered data retrieval, a NETCONF "too-big" error (error-tag: too-big, error-type: transport/rpc/protocol/application, error-severity: error) is acceptable if the data is too large. This would typically be represented as HTTP 413 (Request Entity Too Large) in RESTCONF.