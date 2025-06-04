# Hybrid-MPlane Test Procedure: NETCONF Sessions Verification

## Test Case ID
TC-HMP-003

## Title
Verify that the O-RU has at least two active NETCONF sessions (one towards the O-RU Controller and another towards the O-DU).

## Objective
To confirm that the O-RU maintains at least two active NETCONF sessions by checking the ietf-netconf-monitoring YANG model exposed by the O-RU.

## Scope
This test verifies that:
1. The O-RU exposes the ietf-netconf-monitoring YANG model
2. The O-RU has at least two active NETCONF sessions
3. The O-RU Controller can retrieve this information via RESTCONF

---

## Preconditions
- A NETCONF session between the O-RU and the O-RU Controller is active.
- A NETCONF session between the O-RU and the O-DU is active.
- The O-RU supports the ietf-netconf-monitoring YANG model.
- The O-RU Controller exposes data via RESTCONF in JSON format.
- The test environment supports making RESTCONF requests to the controller.

---

## Test Steps

### Step 1: NETCONF Sessions Retrieval
1. Send a RESTCONF request to retrieve the NETCONF sessions information from the ietf-netconf-monitoring YANG model.
2. Observe the JSON response and verify that it includes the sessions data.

### Step 2: Sessions Count Verification
3. Count the number of active NETCONF sessions in the response.
4. Verify that there are at least two active sessions.

---

## Expected Result
- The RESTCONF request returns a successful response (HTTP 200).
- The response includes the ietf-netconf-monitoring:sessions data.
- The sessions list contains at least two entries, indicating two active NETCONF sessions.

---

## Pass Criteria
- The O-RU exposes the ietf-netconf-monitoring YANG model.
- The O-RU has at least two active NETCONF sessions.
- The JSON response correctly reflects the NETCONF sessions information.

## Fail Criteria
- RESTCONF returns HTTP errors or unexpected/malformed JSON.
- The ietf-netconf-monitoring YANG model is not exposed by the O-RU.
- The O-RU has fewer than two active NETCONF sessions.

---

## Postconditions
- NETCONF sessions remain active and usable for further tests.
- JSON output may be archived as a test artifact.

---

## Test Observables and Artifacts

| Artifact | Description |
|----------|-------------|
| **Sessions JSON** | NETCONF sessions information as exposed via RESTCONF |
| **Session Count** | Number of active NETCONF sessions |
| **Session Details** | Details of each active NETCONF session (ID, username, source host, transport) |
| **Timestamps** | Time of the RESTCONF request and response |
| **Logs (optional)** | Logs from O-RU Controller reflecting NETCONF/RESTCONF flow |

---

## Notes
- This test verifies that the O-RU maintains multiple NETCONF sessions, which is important for proper operation in a disaggregated environment.
- The test expects at least two sessions: one from the O-RU Controller and another from the O-DU.
- The ietf-netconf-monitoring YANG model is a standard model defined in RFC 6022.
- RESTCONF responses are expected in JSON format.